import os
from flask import Flask
from models import db, Url
from controllers import configurar_rotas
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")

db.init_app(app)

with app.app_context():
    db.create_all()

configurar_rotas(app)

if __name__ == "__main__":
    app.run(debug=True)