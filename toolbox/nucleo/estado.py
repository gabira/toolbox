"""Estado global exposto ao QML como `nucleo`: arquivo compartilhado e apps."""

from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from toolbox import __version__
from toolbox.nucleo import arquivo
from toolbox.nucleo.registro import AppRegistrado, carregar_controlador


def _url(caminho: Path) -> str:
    return QUrl.fromLocalFile(str(caminho)).toString()


def _caminho_local(url_ou_caminho: str) -> str:
    url = QUrl(url_ou_caminho)
    return url.toLocalFile() if url.isLocalFile() else url_ou_caminho


class Nucleo(QObject):
    arquivoAlterado = Signal()

    def __init__(self, apps: list[AppRegistrado], pai=None):
        super().__init__(pai)
        self._apps = apps
        self._controladores = {app.id: carregar_controlador(app, self) for app in apps}
        self._arquivo = ""
        self._tipo = ""

    # --- arquivo compartilhado ---

    @Property(str, notify=arquivoAlterado)
    def arquivo(self) -> str:
        return self._arquivo

    @Property(str, notify=arquivoAlterado)
    def nomeArquivo(self) -> str:
        return Path(self._arquivo).name if self._arquivo else ""

    @Property(str, notify=arquivoAlterado)
    def tipoArquivo(self) -> str:
        return self._tipo

    @Property(str, notify=arquivoAlterado)
    def resumoArquivo(self) -> str:
        """Ex.: "vídeo · 24,3 MB"."""
        if not self._arquivo:
            return ""
        try:
            tamanho = arquivo.tamanho_legivel(Path(self._arquivo).stat().st_size)
        except OSError:
            tamanho = "?"
        return f"{arquivo.nome_categoria(self._tipo)} · {tamanho}"

    @Slot(str)
    def definirArquivo(self, url_ou_caminho: str) -> None:
        caminho = _caminho_local(url_ou_caminho)
        if not caminho or not Path(caminho).is_file():
            return
        self._arquivo = str(Path(caminho))
        self._tipo = arquivo.detectar_tipo(caminho)
        self.arquivoAlterado.emit()

    @Slot()
    def limparArquivo(self) -> None:
        if self._arquivo:
            self._arquivo = ""
            self._tipo = ""
            self.arquivoAlterado.emit()

    # --- apps ---

    def _como_mapa(self, app: AppRegistrado) -> dict:
        return {
            "id": app.id,
            "nome": app.nome,
            "descricao": app.descricao,
            "cor": app.cor,
            "icone": _url(app.icone),
            "tela": _url(app.tela),
        }

    @Property("QVariantList", notify=arquivoAlterado)
    def appsVisiveis(self) -> list:
        """Sem arquivo: todos. Com arquivo: só os que aceitam o tipo dele."""
        return [
            self._como_mapa(app) for app in self._apps
            if not self._arquivo or arquivo.compativel(app.tipos_aceitos, self._tipo)
        ]

    @Property(int, constant=True)
    def totalApps(self) -> int:
        return len(self._apps)

    @Slot(str, result=QObject)
    def controlador(self, id_app: str) -> QObject:
        return self._controladores.get(id_app)

    @Property(str, constant=True)
    def versao(self) -> str:
        return __version__
