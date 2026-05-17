from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Index
from datetime import datetime

db = SQLAlchemy()

class Url(db.Model):
    __tablename__ = "url"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    link_original: Mapped[str] = mapped_column(nullable=False)
    link_gerado: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    data_cadastro: Mapped[datetime] = mapped_column(default=datetime.now, nullable=False)
    data_expiracao: Mapped[datetime] = mapped_column(nullable=True)
    ip_origem: Mapped[str] = mapped_column(nullable=True)
    cliques: Mapped[int] = mapped_column(default=0, nullable=False)

    __table_args__ = (
        Index("ix_url_link_gerado_expiracao", "link_gerado", "data_expiracao"),
    )

    @property
    def expirado(self) -> bool:
        if self.data_expiracao is None:
            return False
        return datetime.now() > self.data_expiracao

    def to_dict(self, host_url: str = "") -> dict:
        return {
            "id": self.id,
            "url_original": self.link_original,
            "url_curta": host_url + self.link_gerado,
            "codigo": self.link_gerado,
            "cliques": self.cliques,
            "data_cadastro": self.data_cadastro.strftime("%d/%m/%Y"),
            "expiracao": self.data_expiracao.strftime("%d/%m/%Y") if self.data_expiracao else None,
            "expirado": self.expirado,
        }