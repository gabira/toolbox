"""Preferências do usuário em %APPDATA%\\TOOLBOX\\config.json."""

import json
import os
from pathlib import Path

PASTA_DADOS = Path(os.environ.get("APPDATA", Path.home())) / "TOOLBOX"
ARQUIVO_CONFIG = PASTA_DADOS / "config.json"


def _carregar() -> dict:
    try:
        return json.loads(ARQUIVO_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def ler(chave: str, padrao=None):
    return _carregar().get(chave, padrao)


def gravar(chave: str, valor) -> None:
    dados = _carregar()
    dados[chave] = valor
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    ARQUIVO_CONFIG.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def pasta_downloads() -> Path:
    downloads = Path.home() / "Downloads"
    return downloads if downloads.is_dir() else Path.home()
