from flask import render_template, request, redirect
from models import db, Url
import string
import secrets

def gerar_codigo(tamanho=6):
    caracteres = string.ascii_letters + string.digits
    return ''.join(secrets.choice(caracteres) for _ in range(tamanho))

def configurar_rotas(app):
    
    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            url_original = request.form.get("url")
            
            if not url_original:
                return render_template("index.html", erro="Por favor, insira uma URL válida.")

            codigo = gerar_codigo()
            while Url.query.filter_by(link_gerado=codigo).first():
                codigo = gerar_codigo()

            nova_url = Url(link_original=url_original, link_gerado=codigo)
            db.session.add(nova_url)
            db.session.commit()

            url_curta = request.host_url + codigo 
            
            return render_template("index.html", url_curta=url_curta, url_original=url_original)

        return render_template("index.html")

    @app.route("/<codigo>")
    def redirecionar(codigo):
        url_banco = Url.query.filter_by(link_gerado=codigo).first()
        
        if url_banco:
            return redirect(url_banco.link_original)
            
        return render_template("index.html", erro="URL não encontrada ou expirada.")