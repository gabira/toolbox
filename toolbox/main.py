"""Ponto de entrada: `python -m toolbox [--dev]`."""

import logging
import sys

from PySide6.QtCore import QFileSystemWatcher, Qt, QTimer, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from toolbox import PASTA_PACOTE
from toolbox.nucleo.config import PASTA_DADOS
from toolbox.nucleo.estado import Nucleo
from toolbox.nucleo.registro import descobrir_apps

PASTA_UI = PASTA_PACOTE / "ui"
QML_PRINCIPAL = PASTA_UI / "Main.qml"


def _configurar_log(dev: bool) -> None:
    if dev:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
        return
    # Com pythonw não há console; erros vão para %APPDATA%\TOOLBOX\toolbox.log.
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=PASTA_DADOS / "toolbox.log", level=logging.WARNING, encoding="utf-8",
        format="%(asctime)s %(levelname)s %(message)s",
    )
    sys.excepthook = lambda *erro: logging.critical("Erro não tratado", exc_info=erro)


def _mensagem_qt(_tipo, contexto, mensagem) -> None:
    local = f" ({contexto.file}:{contexto.line})" if contexto.file else ""
    logging.warning("Qt: %s%s", mensagem, local)


class RecarregadorQml:
    """Modo --dev: recarrega a janela quando um .qml/.js/.svg é salvo."""

    def __init__(self, motor: QQmlApplicationEngine):
        self._motor = motor
        self._vigia = QFileSystemWatcher()
        self._atraso = QTimer(singleShot=True, interval=250)
        self._atraso.timeout.connect(self._recarregar)
        self._vigia.fileChanged.connect(lambda _: self._atraso.start())
        self._vigiar()

    def _vigiar(self) -> None:
        arquivos = [
            str(p) for padrao in ("*.qml", "*.js", "*.svg")
            for p in PASTA_PACOTE.rglob(padrao)
        ]
        if self._vigia.files():
            self._vigia.removePaths(self._vigia.files())
        self._vigia.addPaths(arquivos)

    def _recarregar(self) -> None:
        logging.info("Recarregando QML...")
        for janela in self._motor.rootObjects():
            janela.close()
            janela.deleteLater()
        self._motor.clearComponentCache()
        self._motor.load(QUrl.fromLocalFile(str(QML_PRINCIPAL)))
        self._vigiar()  # editores que salvam substituindo o arquivo removem o vigia


def _identificar_no_windows() -> None:
    """Sem isto o Windows agrupa a janela com o pythonw.exe e mostra o ícone do Python na barra de tarefas."""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TOOLBOX.Hub")


def executar() -> None:
    dev = "--dev" in sys.argv
    _configurar_log(dev)
    qInstallMessageHandler(_mensagem_qt)
    _identificar_no_windows()

    app = QGuiApplication(sys.argv)
    app.setApplicationName("TOOLBOX")
    app.setOrganizationName("TOOLBOX")
    app.setWindowIcon(QIcon(str(PASTA_UI / "imagens" / "toolbox.ico")))
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)  # barra de título escura

    nucleo = Nucleo(descobrir_apps())
    nucleo.monitorarAreaTransferencia()
    motor = QQmlApplicationEngine()
    motor.rootContext().setContextProperty("nucleo", nucleo)
    motor.load(QUrl.fromLocalFile(str(QML_PRINCIPAL)))
    if not motor.rootObjects():
        logging.critical("Falha ao carregar a interface (%s)", QML_PRINCIPAL)
        sys.exit(1)

    recarregador = RecarregadorQml(motor) if dev else None  # noqa: F841 — mantém vivo
    codigo = app.exec()
    # O motor QML precisa morrer antes do `nucleo`, senão as ligações leem `null` ao fechar.
    del recarregador, motor
    del nucleo
    sys.exit(codigo)
