"""Ponte entre a Tela.qml do gravador e o serviço de captura/mixagem."""

import logging
import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Property, QCoreApplication, QObject, QTimer, QUrl, Signal, Slot

from toolbox.apps.gravador import servico
from toolbox.nucleo import config
from toolbox.nucleo.tarefa import Tarefa

CHAVE_PASTA = "gravador.pasta"
CHAVE_FORMATO = "gravador.formato"
CHAVE_MIC = "gravador.microfone"
CHAVE_SAIDA = "gravador.saida"
PASTA_BRUTOS = config.PASTA_DADOS / "gravacoes"  # faixas cruas enquanto grava

log = logging.getLogger(__name__)


class Controlador(QObject):
    alterado = Signal()
    alteradoNivel = Signal()

    def __init__(self, pai=None):
        super().__init__(pai)
        self._pasta = config.ler(CHAVE_PASTA) or str(config.pasta_downloads())
        self._formato = config.ler(CHAVE_FORMATO, "flac")
        if self._formato not in servico.FORMATOS:
            self._formato = "flac"
        self._mic_escolhido = config.ler(CHAVE_MIC)      # None = padrão do Windows, "" = não gravar
        self._saida_escolhida = config.ler(CHAVE_SAIDA)
        self._microfones: list[servico.Dispositivo] = []
        self._saidas: list[servico.Dispositivo] = []
        self._nome = servico.nome_padrao()
        self._nome_editado = False  # sem edição, o nome acompanha a hora em que a gravação começa
        self._estado = "pronto"  # pronto | gravando | salvando | concluido | erro
        self._mensagem = ""
        self._arquivo_salvo = ""
        self._gravacao: servico.Gravacao | None = None
        self._duracao = 0.0  # da última gravação, mostrada depois de parar
        self._tarefa = None
        self._relogio = QTimer(self)  # atualiza cronômetro e medidores enquanto grava
        self._relogio.setInterval(50)
        self._relogio.timeout.connect(self.alteradoNivel)
        if app := QCoreApplication.instance():
            app.aboutToQuit.connect(self._salvarAoFechar)

    # --- dispositivos ---

    @Slot()
    def atualizarDispositivos(self) -> None:
        try:
            self._microfones, self._saidas = servico.listar_dispositivos()
        except Exception as erro:  # noqa: BLE001 — sem áudio no Windows vira aviso na tela
            log.exception("Falha ao listar dispositivos")
            self._microfones, self._saidas = [], []
            self._mensagem = f"Não foi possível listar os dispositivos de áudio. {erro}"
        self.alterado.emit()

    @staticmethod
    def _lista(dispositivos, escolhido) -> list:
        # Escolha salva que não existe mais (fone desligado) volta para o padrão.
        nomes = {d.nome for d in dispositivos}
        efetivo = escolhido if escolhido == "" or escolhido in nomes else None
        return [{"nome": d.nome, "padrao": d.padrao,
                 "selecionado": d.nome == efetivo or (efetivo is None and d.padrao)} for d in dispositivos]

    @Property("QVariantList", notify=alterado)
    def microfones(self) -> list:
        return self._lista(self._microfones, self._mic_escolhido)

    @Property("QVariantList", notify=alterado)
    def saidas(self) -> list:
        return self._lista(self._saidas, self._saida_escolhida)

    @Property(bool, notify=alterado)
    def gravarMicrofone(self) -> bool:
        return self._mic_escolhido != "" and bool(self._microfones)

    @Property(bool, notify=alterado)
    def gravarSistema(self) -> bool:
        return self._saida_escolhida != "" and bool(self._saidas)

    def _efetivo(self, escolhido, dispositivos) -> str | None:
        if escolhido == "":
            return ""
        return escolhido if escolhido in {d.nome for d in dispositivos} else None

    @Slot(str)
    def escolherMicrofone(self, nome: str) -> None:
        self._mic_escolhido = nome
        config.gravar(CHAVE_MIC, nome)
        self.alterado.emit()

    @Slot(str)
    def escolherSaida(self, nome: str) -> None:
        self._saida_escolhida = nome
        config.gravar(CHAVE_SAIDA, nome)
        self.alterado.emit()

    @Slot(bool)
    def ativarMicrofone(self, ativo: bool) -> None:
        self.escolherMicrofone(next((d.nome for d in self._microfones if d.padrao), None) if ativo else "")

    @Slot(bool)
    def ativarSistema(self, ativo: bool) -> None:
        self.escolherSaida(next((d.nome for d in self._saidas if d.padrao), None) if ativo else "")

    # --- saída ---

    @Property("QVariantList", constant=True)
    def formatos(self) -> list:
        return [{"id": f.id, "nome": f.nome, "descricao": f.descricao, "selo": f.selo}
                for f in servico.FORMATOS.values()]

    @Property(str, notify=alterado)
    def formato(self) -> str:
        return self._formato

    @Property(str, notify=alterado)
    def extensaoSaida(self) -> str:
        return servico.FORMATOS[self._formato].extensao

    @Property(str, notify=alterado)
    def nomeSaida(self) -> str:
        return self._nome

    @Property(str, notify=alterado)
    def pastaDestino(self) -> str:
        return self._pasta

    @Property(str, notify=alterado)
    def pastaDestinoUrl(self) -> str:
        return QUrl.fromLocalFile(self._pasta).toString()

    @Property(str, notify=alterado)
    def previsaoSaida(self) -> str:
        if not Path(self._pasta).is_dir():
            return ""
        extensao = self.extensaoSaida
        base = servico.limpar_nome(self._nome, extensao) or servico.nome_padrao()
        return servico.caminho_livre(Path(self._pasta), base, extensao).name

    @Slot(str)
    def definirFormato(self, id_formato: str) -> None:
        if id_formato in servico.FORMATOS and id_formato != self._formato:
            self._formato = id_formato
            config.gravar(CHAVE_FORMATO, id_formato)
            self.alterado.emit()

    @Slot(str)
    def definirNome(self, nome: str) -> None:
        if nome != self._nome:
            self._nome, self._nome_editado = nome, True
            self.alterado.emit()

    @Slot(str)
    def definirPasta(self, url: str) -> None:
        pasta = QUrl(url).toLocalFile() or url
        if pasta and Path(pasta).is_dir():
            self._pasta = str(Path(pasta))
            config.gravar(CHAVE_PASTA, self._pasta)
            self.alterado.emit()

    # --- gravação ---

    @Property(str, notify=alterado)
    def estado(self) -> str:
        return self._estado

    @Property(str, notify=alterado)
    def mensagem(self) -> str:
        return self._mensagem

    @Property(str, notify=alteradoNivel)
    def tempo(self) -> str:
        return servico.formatar_tempo(self._gravacao.duracao if self._gravacao else self._duracao)

    @Property(float, notify=alteradoNivel)
    def nivelMicrofone(self) -> float:
        return self._gravacao.nivel("mic") if self._gravacao else 0.0

    @Property(float, notify=alteradoNivel)
    def nivelSistema(self) -> float:
        return self._gravacao.nivel("sistema") if self._gravacao else 0.0

    @Slot()
    def gravar(self) -> None:
        if self._estado in ("gravando", "salvando"):
            return
        self._mensagem, self._arquivo_salvo = "", ""
        if not self._nome_editado:
            self._nome = servico.nome_padrao()
        try:
            self._gravacao = servico.Gravacao(
                PASTA_BRUTOS,
                microfone=self._efetivo(self._mic_escolhido, self._microfones),
                saida=self._efetivo(self._saida_escolhida, self._saidas),
            )
        except Exception as erro:  # noqa: BLE001
            log.exception("Falha ao iniciar a gravação")
            self._estado, self._mensagem = "erro", f"Não foi possível começar a gravar. {erro}"
        else:
            self._estado = "gravando"
            self._relogio.start()
        self.alterado.emit()

    @Slot()
    def parar(self) -> None:
        if self._estado != "gravando":
            return
        faixas = self._encerrarGravacao()
        self._estado = "salvando"
        pasta, formato, nome = self._pasta, self._formato, self._nome
        tarefa = Tarefa(lambda _progresso, _cancelado: servico.mixar(faixas, pasta, formato, nome), self)
        tarefa.concluida.connect(self._aoSalvar)
        tarefa.falhou.connect(self._aoFalhar)
        self._tarefa = tarefa
        tarefa.start()
        self.alterado.emit()
        self.alteradoNivel.emit()

    def _encerrarGravacao(self) -> list:
        self._relogio.stop()
        self._duracao = self._gravacao.duracao
        faixas = list(self._gravacao.parar().values())
        self._gravacao = None
        return faixas

    def _salvarAoFechar(self) -> None:
        """Fechar a janela gravando não perde a gravação: salva antes de sair."""
        if self._estado == "gravando":
            faixas = self._encerrarGravacao()
            try:
                servico.mixar(faixas, self._pasta, self._formato, self._nome)
            except Exception:  # noqa: BLE001 — os brutos ficam em PASTA_BRUTOS
                log.exception("Falha ao salvar a gravação ao fechar")
        elif self._tarefa:
            self._tarefa.wait()

    @Slot(object)
    def _aoSalvar(self, saida) -> None:
        self._tarefa = None
        self._estado, self._arquivo_salvo = "concluido", str(saida)
        self._mensagem = f"Gravação salva como {Path(saida).name}"
        self._nome, self._nome_editado = servico.nome_padrao(), False  # pronto para a próxima
        self.alterado.emit()

    @Slot(str)
    def _aoFalhar(self, mensagem: str) -> None:
        self._tarefa = None
        self._estado, self._mensagem = "erro", mensagem
        self.alterado.emit()

    @Slot()
    def abrirArquivo(self) -> None:
        if self._arquivo_salvo and Path(self._arquivo_salvo).exists():
            os.startfile(self._arquivo_salvo)

    @Slot()
    def abrirPasta(self) -> None:
        if self._arquivo_salvo and Path(self._arquivo_salvo).exists():
            subprocess.Popen(["explorer", "/select,", self._arquivo_salvo])
        else:
            os.startfile(self._pasta)
