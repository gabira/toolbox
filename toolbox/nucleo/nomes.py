"""Nomes de arquivos de saída: válidos no Windows e sem sobrescrever nada."""

import re
from pathlib import Path

_INVALIDOS_WINDOWS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVADOS_WINDOWS = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                       *(f"LPT{i}" for i in range(1, 10))}


def limpar_nome(nome: str | None, extensao: str = "") -> str:
    """Deixa o nome digitado válido como nome de arquivo do Windows ("" se não sobrar nada)."""
    nome = _INVALIDOS_WINDOWS.sub("", nome or "").strip()
    # Quem digita "musica.m4a" quer "musica", não "musica.m4a.m4a".
    if extensao and nome.lower().endswith("." + extensao.lower()):
        nome = nome[: -len(extensao) - 1]
    nome = nome.rstrip(". ")[:180]
    if nome.upper() in _RESERVADOS_WINDOWS:
        nome += "_"
    return nome


def caminho_livre(pasta: Path, nome_base: str, extensao: str) -> Path:
    """Nunca sobrescreve: "video.m4a", "video (2).m4a", "video (3).m4a"..."""
    candidato = pasta / f"{nome_base}.{extensao}"
    numero = 2
    while candidato.exists():
        candidato = pasta / f"{nome_base} ({numero}).{extensao}"
        numero += 1
    return candidato
