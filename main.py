import os
import logging
from flask import Flask
from models import db
from controllers import configurar_rotas
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
}

db.init_app(app)

with app.app_context():
    db.create_all()

configurar_rotas(app)

if __name__ == "__main__":
    app.run(debug=True)