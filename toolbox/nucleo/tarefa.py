"""Execução de trabalhos demorados fora da thread da interface."""

from PySide6.QtCore import QCoreApplication, QThread, Signal

from toolbox.nucleo.erros import Cancelado


class Tarefa(QThread):
    """Roda `funcao(ao_progresso, cancelado)` numa thread e emite o resultado.

    - `ao_progresso(fracao)` recebe valores entre 0 e 1.
    - `cancelado()` retorna True depois de `cancelar()` ser chamado.
    """

    progresso = Signal(float)
    concluida = Signal(object)
    falhou = Signal(str)
    cancelada = Signal()

    def __init__(self, funcao, pai=None):
        super().__init__(pai)
        self._funcao = funcao
        self._cancelar = False
        self.finished.connect(self.deleteLater)
        # Fechar a janela no meio de uma tarefa: cancela e espera a thread terminar.
        if app := QCoreApplication.instance():
            app.aboutToQuit.connect(self._encerrar)

    def cancelar(self) -> None:
        self._cancelar = True

    def _encerrar(self) -> None:
        self.cancelar()
        self.wait(5000)

    def run(self) -> None:
        try:
            resultado = self._funcao(self.progresso.emit, lambda: self._cancelar)
        except Cancelado:
            self.cancelada.emit()
        except Exception as erro:  # noqa: BLE001 — qualquer falha vira mensagem na UI
            self.falhou.emit(str(erro) or erro.__class__.__name__)
        else:
            self.concluida.emit(resultado)
