"""Descoberta dos apps em toolbox/apps/<id>/manifesto.json."""

import importlib
import json
from dataclasses import dataclass
from pathlib import Path

from toolbox import PASTA_PACOTE

PASTA_APPS = PASTA_PACOTE / "apps"


@dataclass
class AppRegistrado:
    id: str
    nome: str
    descricao: str
    cor: str
    tipos_aceitos: list[str]
    ordem: int
    pasta: Path
    precisa_arquivo: bool = True  # False = trabalha com link/texto; aparece sempre no hub

    @property
    def icone(self) -> Path:
        return self.pasta / "icone.svg"

    @property
    def tela(self) -> Path:
        return self.pasta / "Tela.qml"


def descobrir_apps(pasta_apps: Path = PASTA_APPS) -> list[AppRegistrado]:
    apps = []
    for manifesto in sorted(pasta_apps.glob("*/manifesto.json")):
        dados = json.loads(manifesto.read_text(encoding="utf-8"))
        apps.append(AppRegistrado(
            id=manifesto.parent.name,
            nome=dados["nome"],
            descricao=dados.get("descricao", ""),
            cor=dados.get("cor", "#3B82F6"),
            tipos_aceitos=dados.get("tipos_aceitos", ["*"]),
            ordem=dados.get("ordem", 100),
            pasta=manifesto.parent,
            precisa_arquivo=dados.get("precisa_arquivo", True),
        ))
    return sorted(apps, key=lambda app: (app.ordem, app.nome))


def carregar_controlador(app: AppRegistrado, pai):
    """Importa toolbox.apps.<id>.controlador e instancia a classe Controlador."""
    modulo = importlib.import_module(f"toolbox.apps.{app.id}.controlador")
    return modulo.Controlador(pai)
