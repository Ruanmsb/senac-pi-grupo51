import os
import string
import secrets
import logging
from urllib.parse import urlparse
from datetime import datetime, timedelta, date
from functools import wraps

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
_MAX_URL_LENGTH = 2048
_TTL_DIAS_MAXIMO = 365
_API_KEY = os.getenv("API_KEY", "")

def _gerar_codigo(tamanho: int = _TAMANHO_CODIGO) -> str:
    caracteres = string.ascii_letters + string.digits
    return "".join(secrets.choice(caracteres) for _ in range(tamanho))

def _sanitizar_url(url: str) -> tuple[bool, str]:
    url = url.strip()
    if not url:
        return False, "Por favor, insira uma URL."
    if len(url) > _MAX_URL_LENGTH:
        return False, f"URL muito longa (máximo {_MAX_URL_LENGTH} caracteres)."
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
        logger.warning("Rate limit excedido para IP: %s", ip)
        _rate_limit_store[ip] = historico
        return True
    historico.append(agora)
    _rate_limit_store[ip] = historico
    return False

def _validar_api_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not _API_KEY:
            logger.info("Requisição de dados sem autenticação (API_KEY não configurada)")
            return f(*args, **kwargs)
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            logger.warning("Tentativa de acesso sem token Bearer")
            return jsonify({"erro": "Autenticação obrigatória"}), 401
        token = auth.split(" ", 1)[1]
        if token != _API_KEY:
            logger.warning("Tentativa de acesso com token inválido")
            return jsonify({"erro": "Token inválido"}), 403
        return f(*args, **kwargs)
    return wrapper

def _calcular_expiracao() -> datetime | None:
    if _TTL_DIAS <= 0:
        return None
    if _TTL_DIAS > _TTL_DIAS_MAXIMO:
        logger.warning("TTL_DIAS=%d excede máximo %d, usando máximo", _TTL_DIAS, _TTL_DIAS_MAXIMO)
        return datetime.now() + timedelta(days=_TTL_DIAS_MAXIMO)
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
            logger.info("URL gerada com sucesso: %s → %s (tentativa %d | IP: %s)", url_original, codigo, tentativa, ip)
            return nova_url
        except IntegrityError:
            db.session.rollback()
            logger.debug("Colisão de código detectada, tentando novamente... (tentativa %d/%d)", tentativa, _MAX_TENTATIVAS_COLISAO)
    logger.error("Falha ao gerar código único após %d tentativas para IP: %s", _MAX_TENTATIVAS_COLISAO, ip)
    raise RuntimeError(f"Não foi possível gerar código único após {_MAX_TENTATIVAS_COLISAO} tentativas.")


def configurar_rotas(app):

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/encurtar", methods=["POST"])
    def api_encurtar():
        """
        Encurta uma URL e retorna o código gerado.
        ---
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              properties:
                url:
                  type: string
                  example: "https://exemplo.com/pagina-muito-longa"
        responses:
          201:
            description: URL encurtada com sucesso
            schema:
              type: object
              properties:
                url_original:
                  type: string
                url_curta:
                  type: string
                cliques:
                  type: integer
          400:
            description: URL inválida ou validação falhou
          429:
            description: Limite de taxa excedido
          500:
            description: Erro interno do servidor
        """
        ip = request.remote_addr or "desconhecido"
        if _checar_rate_limit(ip):
            logger.warning("Rate limit acionado para IP: %s", ip)
            return jsonify({"erro": f"Limite de {_RATE_LIMIT_MAX_REQUISICOES} encurtamentos por {_RATE_LIMIT_JANELA_SEGUNDOS}s atingido."}), 429

        dados = request.get_json(silent=True) or {}
        url_original = (dados.get("url") or "").strip()

        valida, mensagem_erro = _sanitizar_url(url_original)
        if not valida:
            logger.info("URL inválida de IP %s: %s", ip, mensagem_erro)
            return jsonify({"erro": mensagem_erro}), 400

        try:
            nova_url = _salvar_url(url_original, ip)
            return jsonify(nova_url.to_dict(request.host_url)), 201
        except RuntimeError as exc:
            logger.error("Erro ao salvar URL: %s", exc)
            return jsonify({"erro": "Erro interno. Tente novamente."}), 500
        except Exception as exc:
            logger.exception("Exceção inesperada em api_encurtar: %s", exc)
            return jsonify({"erro": "Erro interno não previsto."}), 500

    @app.route("/api/stats")
    @_validar_api_key
    def api_stats():
        """
        Retorna estatísticas gerais de uso (requer autenticação se API_KEY configurada).
        ---
        responses:
          200:
            description: Estatísticas recuperadas
            schema:
              type: object
              properties:
                total_links:
                  type: integer
                total_cliques:
                  type: integer
                hoje:
                  type: integer
          401:
            description: Autenticação obrigatória
          403:
            description: Token inválido
        """
        try:
            total_links = db.session.query(func.count(Url.id)).scalar() or 0
            total_cliques = db.session.query(func.sum(Url.cliques)).scalar() or 0
            hoje = db.session.query(func.count(Url.id)).filter(
                func.date(Url.data_cadastro) == date.today()
            ).scalar() or 0
            logger.info("Estatísticas recuperadas com sucesso")
            return jsonify({
                "total_links": total_links,
                "total_cliques": total_cliques,
                "hoje": hoje,
            }), 200
        except Exception as exc:
            logger.exception("Erro ao recuperar estatísticas: %s", exc)
            return jsonify({"erro": "Erro ao recuperar dados."}), 500

    @app.route("/api/links", methods=["GET"])
    @_validar_api_key
    def api_links():
        """
        Lista os últimos 50 links criados (requer autenticação se API_KEY configurada).
        ---
        responses:
          200:
            description: Lista de links
          401:
            description: Autenticação obrigatória
          403:
            description: Token inválido
          500:
            description: Erro ao listar links
        """
        try:
            links = Url.query.order_by(Url.data_cadastro.desc()).limit(50).all()
            logger.info("Listagem de links realizada: %d links retornados", len(links))
            return jsonify([l.to_dict(request.host_url) for l in links]), 200
        except Exception as exc:
            logger.exception("Erro ao listar links: %s", exc)
            return jsonify({"erro": "Erro ao listar links."}), 500

    @app.route("/api/links/<int:link_id>", methods=["DELETE"])
    def api_excluir(link_id):
        """
        Deleta um link específico.
        ---
        parameters:
          - name: link_id
            in: path
            type: integer
            required: true
        responses:
          200:
            description: Link deletado com sucesso
          404:
            description: Link não encontrado
          500:
            description: Erro ao deletar
        """
        try:
            url = Url.query.get_or_404(link_id)
            logger.info("Deletando link ID %d (código: %s)", link_id, url.link_gerado)
            db.session.delete(url)
            db.session.commit()
            logger.info("Link ID %d deletado com sucesso", link_id)
            return jsonify({"ok": True}), 200
        except Exception as exc:
            logger.exception("Erro ao deletar link ID %d: %s", link_id, exc)
            return jsonify({"erro": "Erro ao deletar link."}), 500

    @app.route("/<path:codigo>")
    def redirecionar(codigo):
        if codigo.startswith("api/"):
            return jsonify({"erro": "Rota não encontrada."}), 404

        try:
            url_banco = Url.query.filter_by(link_gerado=codigo).first()
            if not url_banco:
                logger.info("Código não encontrado: %s", codigo)
                return render_template("index.html"), 404
            if url_banco.expirado:
                logger.info("Link expirado acessado: %s", codigo)
                return render_template("index.html"), 410
            url_banco.cliques += 1
            db.session.commit()
            logger.info("Redirecionamento realizado: %s → %s (total de cliques: %d)", codigo, url_banco.link_original, url_banco.cliques)
            return redirect(url_banco.link_original)
        except Exception as exc:
            logger.exception("Erro ao processar redirecionamento de código %s: %s", codigo, exc)
            return render_template("index.html"), 500

    @app.cli.command("limpar-expirados")
    def limpar_expirados():
        agora = datetime.now()
        removidos = Url.query.filter(
            Url.data_expiracao.isnot(None),
            Url.data_expiracao < agora,
        ).delete(synchronize_session=False)
        db.session.commit()
        print(f"{removidos} link(s) expirado(s) removido(s).")
        logger.info("Limpeza de expirados realizada: %d links removidos", removidos)