"""TOOLBOX — hub de ferramentas locais para arquivos."""

from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_PACOTE = Path(__file__).resolve().parent

__version__ = (RAIZ_PROJETO / "VERSION").read_text(encoding="utf-8").strip()
