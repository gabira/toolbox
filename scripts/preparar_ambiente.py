"""Instala as dependências do .venv somente quando o arquivo de requisitos muda.

Chamado pelo iniciar.bat com o Python do .venv. Guarda o hash do arquivo de
requisitos em .venv/.hash-<modo> para que as próximas execuções sejam instantâneas.
"""

import hashlib
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def main() -> int:
    dev = "--dev" in sys.argv
    requisitos = RAIZ / ("requirements-dev.txt" if dev else "requirements.txt")
    arquivo_hash = RAIZ / ".venv" / (".hash-dev" if dev else ".hash")

    # O requirements-dev inclui o requirements.txt, então os dois entram no hash.
    conteudo = b"".join(
        (RAIZ / nome).read_bytes()
        for nome in ("requirements.txt", requisitos.name)
    )
    hash_atual = hashlib.sha256(conteudo).hexdigest()

    if arquivo_hash.exists() and arquivo_hash.read_text().strip() == hash_atual:
        return 0

    print("[TOOLBOX] Instalando dependências (só acontece quando elas mudam)...")
    resultado = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
         "-q", "-r", str(requisitos)],
        cwd=RAIZ,
    )
    if resultado.returncode != 0:
        return resultado.returncode

    arquivo_hash.write_text(hash_atual)
    print("[TOOLBOX] Dependências prontas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
