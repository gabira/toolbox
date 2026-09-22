"""Estado global exposto ao QML como `nucleo`: a entrada compartilhada e os apps.

A entrada é híbrida: um arquivo OU um/vários links. Links ganham um tipo no
mesmo formato dos arquivos ("link/youtube"), então o filtro de apps é um só.
"""

from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication

from toolbox import __version__
from toolbox.nucleo import arquivo, link
from toolbox.nucleo.registro import AppRegistrado, carregar_controlador, carregar_filtro


def _url(caminho: Path) -> str:
    return QUrl.fromLocalFile(str(caminho)).toString()


def _caminho_local(url_ou_caminho: str) -> str:
    url = QUrl(url_ou_caminho)
    return url.toLocalFile() if url.isLocalFile() else url_ou_caminho


class Nucleo(QObject):
    entradaAlterada = Signal()
    linkCopiadoAlterado = Signal()

    def __init__(self, apps: list[AppRegistrado], pai=None):
        super().__init__(pai)
        self._apps = apps
        self._controladores = {app.id: carregar_controlador(app, self) for app in apps}
        self._filtros = {app.id: carregar_filtro(app) for app in apps}
        self._arquivo = ""
        self._links: list[str] = []
        self._tipo = ""
        # Link do YouTube encontrado na área de transferência (oferecido ao usuário)
        self._links_copiados: list[str] = []
        self._copias_dispensadas: set[tuple] = set()

    # ------------------------------------------------------------ entrada

    @Property(str, notify=entradaAlterada)
    def tipoEntrada(self) -> str:
        """"" (vazia), "arquivo" ou "link"."""
        return "arquivo" if self._arquivo else ("link" if self._links else "")

    @Property(str, notify=entradaAlterada)
    def nomeEntrada(self) -> str:
        if self._arquivo:
            return Path(self._arquivo).name
        if len(self._links) == 1:
            return link.rotulo_curto(self._links[0])
        return link.descrever(self._links)

    @Property(str, notify=entradaAlterada)
    def resumoEntrada(self) -> str:
        return self.resumoArquivo if self._arquivo else link.descrever(self._links)

    @Slot(str, result=str)
    def definirTexto(self, texto: str) -> str:
        """Texto colado/digitado: caminho de arquivo ou links. Retorna mensagem de erro ou ""."""
        # Um caminho de arquivo que existe vale como arquivo, mesmo que o nome pareça um link.
        caminho = _caminho_local((texto or "").strip().strip('"'))
        if caminho and Path(caminho).is_file():
            self.definirArquivo(caminho)
            return ""
        links = link.extrair_links(texto)
        if links:
            youtube = [l for l in links if link.e_youtube(l)]
            self._definir_links(youtube or links)
            return ""
        return "Não reconheci um arquivo ou link nesse texto."

    def _definir_links(self, links: list[str]) -> None:
        self._arquivo = ""
        self._links = links
        self._tipo = link.tipo_links(links)
        if self._links_copiados == links:
            self._dispensar_copia()
        self.entradaAlterada.emit()

    @Slot()
    def limparEntrada(self) -> None:
        if self._arquivo or self._links:
            self._arquivo, self._links, self._tipo = "", [], ""
            self.entradaAlterada.emit()

    # --- arquivo ---

    @Property(str, notify=entradaAlterada)
    def arquivo(self) -> str:
        return self._arquivo

    @Property(str, notify=entradaAlterada)
    def nomeArquivo(self) -> str:
        return Path(self._arquivo).name if self._arquivo else ""

    @Property(str, notify=entradaAlterada)
    def tipoArquivo(self) -> str:
        return self._tipo if self._arquivo else ""

    @Property(str, notify=entradaAlterada)
    def resumoArquivo(self) -> str:
        """Ex.: "vídeo · 24,3 MB"."""
        if not self._arquivo:
            return ""
        try:
            tamanho = arquivo.tamanho_legivel(Path(self._arquivo).stat().st_size)
        except OSError:
            tamanho = "?"
        return f"{arquivo.descrever_tipo(self._tipo)} · {tamanho}"

    @Slot(str)
    def definirArquivo(self, url_ou_caminho: str) -> None:
        caminho = _caminho_local(url_ou_caminho)
        if not caminho or not Path(caminho).is_file():
            return
        self._links = []
        self._arquivo = str(Path(caminho))
        self._tipo = arquivo.detectar_tipo(caminho)
        self.entradaAlterada.emit()

    # --- links ---

    @Property("QVariantList", notify=entradaAlterada)
    def links(self) -> list:
        return self._links

    # ------------------------------------------------------------ área de transferência

    def monitorarAreaTransferencia(self) -> None:
        """Oferece usar links do YouTube copiados (agora e sempre que o usuário copiar outro)."""
        area = QGuiApplication.clipboard()
        area.dataChanged.connect(self._verificarAreaTransferencia)
        QTimer.singleShot(1600, self._verificarAreaTransferencia)  # depois da abertura

    @Slot()
    def _verificarAreaTransferencia(self) -> None:
        links = [l for l in link.extrair_links(QGuiApplication.clipboard().text()) if link.e_youtube(l)]
        if not links or links == self._links or tuple(links) in self._copias_dispensadas:
            return
        if links != self._links_copiados:
            self._links_copiados = links
            self.linkCopiadoAlterado.emit()

    @Property(str, notify=linkCopiadoAlterado)
    def linkCopiado(self) -> str:
        return link.rotulo_curto(self._links_copiados[0]) if len(self._links_copiados) == 1 else (
            link.descrever(self._links_copiados))

    @Property(str, notify=linkCopiadoAlterado)
    def resumoLinkCopiado(self) -> str:
        return link.descrever(self._links_copiados)

    @Slot()
    def usarLinkCopiado(self) -> None:
        if self._links_copiados:
            self._definir_links(list(self._links_copiados))

    @Slot()
    def ignorarLinkCopiado(self) -> None:
        self._dispensar_copia()

    def _dispensar_copia(self) -> None:
        if self._links_copiados:
            self._copias_dispensadas.add(tuple(self._links_copiados))
            self._links_copiados = []
            self.linkCopiadoAlterado.emit()

    @Slot(result=str)
    def colarAreaTransferencia(self) -> str:
        """Ctrl+V no hub: arquivo copiado no Explorer, link ou caminho de arquivo."""
        dados = QGuiApplication.clipboard().mimeData()
        if dados and dados.hasUrls():
            locais = [u.toLocalFile() for u in dados.urls() if u.isLocalFile()]
            if locais:
                self.definirArquivo(locais[0])
                return ""
        return self.definirTexto(dados.text() if dados else "")

    # ------------------------------------------------------------ apps

    def _como_mapa(self, app: AppRegistrado) -> dict:
        return {
            "id": app.id,
            "nome": app.nome,
            "descricao": app.descricao,
            "cor": app.cor,
            "icone": _url(app.icone),
            "tela": _url(app.tela),
            "aceitaLink": any(tipo.startswith("link/") for tipo in app.tipos_aceitos),
        }

    def _aceita_entrada_atual(self, app: AppRegistrado) -> bool:
        if self._arquivo and not app.precisa_arquivo:
            return False  # apps de link não trabalham com o arquivo em si
        if not self._tipo or not arquivo.compativel(app.tipos_aceitos, self._tipo):
            return False
        filtro = self._filtros.get(app.id)
        return filtro is None or bool(filtro(self._arquivo or None, self._tipo))

    @Property("QVariantList", notify=entradaAlterada)
    def appsVisiveis(self) -> list:
        """Sem entrada: todos. Com arquivo ou link: só os que aceitam aquela entrada.

        Ex.: o Baixar do YouTube só aparece para links do YouTube, nunca para um arquivo.
        """
        return [
            self._como_mapa(app) for app in self._apps
            if not self.tipoEntrada or self._aceita_entrada_atual(app)
        ]

    @Property(int, notify=entradaAlterada)
    def totalCompativeis(self) -> int:
        """Quantos apps trabalham com a entrada atual."""
        return sum(1 for app in self._apps if self._aceita_entrada_atual(app))

    @Property(int, constant=True)
    def totalApps(self) -> int:
        return len(self._apps)

    @Slot(str, result=QObject)
    def controlador(self, id_app: str) -> QObject:
        return self._controladores.get(id_app)

    @Property(str, constant=True)
    def versao(self) -> str:
        return __version__
