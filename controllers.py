import os
import string
import secrets
import logging
from urllib.parse import urlparse
from datetime import datetime, timedelta, date

from flask import render_template, request, redirect, jsonify
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from models import db, Url

logger = logging.getLogger(__name__)

_ESQUEMAS_PERMITIDOS = {"http", "https"}
_DOMINIOS_BLOQUEADOS = {"malware.com", "phishing.net"}
_rate_limit_store: dict[str, list[datetime]] = {}

_RATE_LIMIT_JANELA_SEGUNDOS = int(os.getenv("RATE_LIMIT_JANELA_SEGUNDOS", "60"))
_RATE_LIMIT_MAX_REQUISICOES = int(os.getenv("RATE_LIMIT_MAX_REQUISICOES", "10"))
_TTL_DIAS = int(os.getenv("URL_TTL_DIAS", "30"))
_TAMANHO_CODIGO = int(os.getenv("URL_CODIGO_TAMANHO", "6"))
_MAX_TENTATIVAS_COLISAO = 10

def _gerar_codigo(tamanho: int = _TAMANHO_CODIGO) -> str:
    caracteres = string.ascii_letters + string.digits
    return "".join(secrets.choice(caracteres) for _ in range(tamanho))

def _sanitizar_url(url: str) -> tuple[bool, str]:
    url = url.strip()
    if not url:
        return False, "Por favor, insira uma URL."
    parsed = urlparse(url)
    if parsed.scheme not in _ESQUEMAS_PERMITIDOS:
        return False, f"Esquema '{parsed.scheme}' não permitido. Use http:// ou https://."
    if not parsed.netloc:
        return False, "URL inválida: domínio não encontrado."
    dominio = parsed.netloc.lower().split(":")[0]
    if dominio in _DOMINIOS_BLOQUEADOS:
        return False, "Esta URL não pode ser encurtada por razões de segurança."
    return True, ""

def _checar_rate_limit(ip: str) -> bool:
    agora = datetime.now()
    janela = timedelta(seconds=_RATE_LIMIT_JANELA_SEGUNDOS)
    historico = [ts for ts in _rate_limit_store.get(ip, []) if agora - ts < janela]
    if len(historico) >= _RATE_LIMIT_MAX_REQUISICOES:
        _rate_limit_store[ip] = historico
        return True
    historico.append(agora)
    _rate_limit_store[ip] = historico
    return False


def _calcular_expiracao() -> datetime | None:
    if _TTL_DIAS <= 0:
        return None
    return datetime.now() + timedelta(days=_TTL_DIAS)

def _salvar_url(url_original: str, ip: str) -> Url:
    for tentativa in range(1, _MAX_TENTATIVAS_COLISAO + 1):
        codigo = _gerar_codigo()
        nova_url = Url(
            link_original=url_original,
            link_gerado=codigo,
            data_expiracao=_calcular_expiracao(),
            ip_origem=ip,
            cliques=0,
        )
        try:
            db.session.add(nova_url)
            db.session.commit()
            logger.info("URL gerada: %s → %s (tentativa %d)", url_original, codigo, tentativa)
            return nova_url
        except IntegrityError:
            db.session.rollback()
    raise RuntimeError(f"Não foi possível gerar código único após {_MAX_TENTATIVAS_COLISAO} tentativas.")


def configurar_rotas(app):

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/encurtar", methods=["POST"])
    def api_encurtar():
        ip = request.remote_addr or "desconhecido"
        if _checar_rate_limit(ip):
            return jsonify({"erro": f"Limite de {_RATE_LIMIT_MAX_REQUISICOES} encurtamentos por {_RATE_LIMIT_JANELA_SEGUNDOS}s atingido."}), 429

        dados = request.get_json(silent=True) or {}
        url_original = (dados.get("url") or "").strip()

        valida, mensagem_erro = _sanitizar_url(url_original)
        if not valida:
            return jsonify({"erro": mensagem_erro}), 400

        try:
            nova_url = _salvar_url(url_original, ip)
        except RuntimeError as exc:
            logger.error("Erro ao salvar URL: %s", exc)
            return jsonify({"erro": "Erro interno. Tente novamente."}), 500

        return jsonify(nova_url.to_dict(request.host_url)), 201

    @app.route("/api/stats")
    def api_stats():
        total_links = db.session.query(func.count(Url.id)).scalar() or 0
        total_cliques = db.session.query(func.sum(Url.cliques)).scalar() or 0
        hoje = db.session.query(func.count(Url.id)).filter(
            func.date(Url.data_cadastro) == date.today()
        ).scalar() or 0
        return jsonify({
            "total_links": total_links,
            "total_cliques": total_cliques,
            "hoje": hoje,
        })

    @app.route("/api/links", methods=["GET"])
    def api_links():
        links = Url.query.order_by(Url.data_cadastro.desc()).limit(50).all()
        return jsonify([l.to_dict(request.host_url) for l in links])

    @app.route("/api/links/<int:link_id>", methods=["DELETE"])
    def api_excluir(link_id):
        url = Url.query.get_or_404(link_id)
        db.session.delete(url)
        db.session.commit()
        return jsonify({"ok": True})

    @app.route("/<path:codigo>")
    def redirecionar(codigo):
        if codigo.startswith("api/"):
            return jsonify({"erro": "Rota não encontrada."}), 404

        url_banco = Url.query.filter_by(link_gerado=codigo).first()
        if not url_banco:
            return render_template("index.html"), 404
        if url_banco.expirado:
            return render_template("index.html"), 410
        url_banco.cliques += 1
        db.session.commit()
        return redirect(url_banco.link_original)

    @app.cli.command("limpar-expirados")
    def limpar_expirados():
        agora = datetime.now()
        removidos = Url.query.filter(
            Url.data_expiracao.isnot(None),
            Url.data_expiracao < agora,
        ).delete(synchronize_session=False)
        db.session.commit()
        print(f"{removidos} link(s) expirado(s) removido(s).")