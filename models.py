from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

db = SQLAlchemy()

class Url(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    link_original: Mapped[str] = mapped_column(nullable=False)
    link_gerado: Mapped[str] = mapped_column(nullable=False, unique=True)
    data_cadastro: Mapped[datetime] = mapped_column(default=datetime.now, nullable=False)