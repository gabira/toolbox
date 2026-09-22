"""Ponte entre a Tela.qml do separador e o serviço de extração."""

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from toolbox.apps.separador_audio import servico
from toolbox.nucleo import arquivo, config
from toolbox.nucleo.ffmpeg import sondar
from toolbox.nucleo.tarefa import Tarefa

CHAVE_PASTA = "separador_audio.pasta"
CHAVE_FORMATO = "separador_audio.formato"


class Controlador(QObject):
    alterado = Signal()

    def __init__(self, pai=None):
        super().__init__(pai)
        self._pasta = config.ler(CHAVE_PASTA) or str(config.pasta_downloads())
        self._formato = config.ler(CHAVE_FORMATO, "original")
        if self._formato not in servico.FORMATOS:
            self._formato = "original"
        self._analise = {"estado": "vazio"}
        self._arquivo = ""
        self._nome = ""            # nome de saída (sem extensão) mostrado no campo
        self._codec = ""
        self._tarefa_analise = None
        self._tarefa_extracao = None
        self._estado = "pronto"  # pronto | extraindo | concluido | erro
        self._progresso = 0.0
        self._mensagem = ""
        self._saida = ""

    # --- propriedades lidas pelo QML ---

    @Property("QVariantMap", notify=alterado)
    def analise(self) -> dict:
        return self._analise

    @Property("QVariantList", constant=True)
    def formatos(self) -> list:
        return [
            {"id": f.id, "nome": f.nome, "descricao": f.descricao, "selo": f.selo}
            for f in servico.FORMATOS.values()
        ]

    @Property(str, notify=alterado)
    def formato(self) -> str:
        return self._formato

    @Property(str, notify=alterado)
    def pastaDestino(self) -> str:
        return self._pasta

    @Property(str, notify=alterado)
    def pastaDestinoUrl(self) -> str:
        return QUrl.fromLocalFile(self._pasta).toString()

    @Property(str, notify=alterado)
    def nomeSaida(self) -> str:
        return self._nome

    @Property(str, notify=alterado)
    def nomePadrao(self) -> str:
        return Path(self._arquivo).stem if self._arquivo else ""

    @Property(str, notify=alterado)
    def extensaoSaida(self) -> str:
        if not self._codec:
            return ""
        return servico.extensao_saida(servico.FORMATOS[self._formato], self._codec)

    @Property(str, notify=alterado)
    def previsaoSaida(self) -> str:
        """Nome final do arquivo, já com extensão e numeração se o nome existir."""
        extensao = self.extensaoSaida
        if not extensao or not Path(self._pasta).is_dir():
            return ""
        base = servico.limpar_nome(self._nome, extensao) or self.nomePadrao
        return servico.caminho_livre(Path(self._pasta), base, extensao).name

    @Property(str, notify=alterado)
    def estado(self) -> str:
        return self._estado

    @Property(float, notify=alterado)
    def progresso(self) -> float:
        return self._progresso

    @Property(str, notify=alterado)
    def mensagem(self) -> str:
        return self._mensagem

    # --- análise do vídeo ---

    @Slot(str)
    def analisar(self, caminho: str) -> None:
        self._tarefa_analise = None
        if self._estado in ("concluido", "erro"):
            self._estado, self._mensagem = "pronto", ""
        if caminho != self._arquivo:
            # Vídeo novo: o campo de nome começa com o nome dele.
            self._arquivo = caminho
            self._nome = Path(caminho).stem if caminho else ""
        self._codec = ""

        if not caminho:
            self._analise = {"estado": "vazio"}
        elif not arquivo.detectar_tipo(caminho).startswith("video/"):
            self._analise = {"estado": "erro", "mensagem": "O arquivo atual não é um vídeo."}
        else:
            self._analise = {"estado": "analisando"}
            tarefa = Tarefa(lambda _progresso, _cancelado: sondar(caminho), self)
            tarefa.concluida.connect(self._aoAnalisar)
            tarefa.falhou.connect(self._aoFalharAnalise)
            self._tarefa_analise = tarefa
            tarefa.start()
        self.alterado.emit()

    @Slot(object)
    def _aoAnalisar(self, info) -> None:
        if self.sender() is not self._tarefa_analise:
            return  # resultado de um arquivo que já foi trocado
        self._tarefa_analise = None
        if not info.faixas_audio:
            self._analise = {"estado": "erro", "mensagem": "Este vídeo não tem trilha de áudio."}
        else:
            faixa = info.faixas_audio[0]
            self._codec = faixa.codec
            self._analise = {
                "estado": "ok",
                "codec": servico.nome_codec(faixa.codec),
                "detalhes": servico.detalhes_faixa(faixa),
                "faixas": len(info.faixas_audio),
                "duracao": servico.formatar_duracao(info.duracao_s),
                "extensao": servico.extensao_original(faixa.codec),
            }
        self.alterado.emit()

    @Slot(str)
    def _aoFalharAnalise(self, mensagem: str) -> None:
        if self.sender() is not self._tarefa_analise:
            return
        self._tarefa_analise = None
        self._analise = {"estado": "erro", "mensagem": f"Não foi possível ler o vídeo. {mensagem}"}
        self.alterado.emit()

    # --- preferências ---

    @Slot(str)
    def definirFormato(self, id_formato: str) -> None:
        if id_formato in servico.FORMATOS and id_formato != self._formato:
            self._formato = id_formato
            config.gravar(CHAVE_FORMATO, id_formato)
            self.alterado.emit()

    @Slot(str)
    def definirNome(self, nome: str) -> None:
        if nome != self._nome:
            self._nome = nome
            self.alterado.emit()

    @Slot(str)
    def definirPasta(self, url: str) -> None:
        pasta = QUrl(url).toLocalFile() or url
        if pasta and Path(pasta).is_dir():
            self._pasta = str(Path(pasta))
            config.gravar(CHAVE_PASTA, self._pasta)
            self.alterado.emit()

    # --- extração ---

    @Slot(str)
    def extrair(self, caminho: str) -> None:
        if self._estado == "extraindo" or self._analise.get("estado") != "ok":
            return
        self._estado, self._progresso, self._mensagem, self._saida = "extraindo", 0.0, "", ""
        pasta, formato, nome = self._pasta, self._formato, self._nome
        tarefa = Tarefa(
            lambda ao_progresso, cancelado: servico.extrair(
                caminho, pasta, formato, ao_progresso, cancelado, nome=nome),
            self,
        )
        tarefa.progresso.connect(self._aoProgredir)
        tarefa.concluida.connect(self._aoConcluir)
        tarefa.falhou.connect(self._aoFalhar)
        tarefa.cancelada.connect(self._aoCancelar)
        self._tarefa_extracao = tarefa
        tarefa.start()
        self.alterado.emit()

    @Slot()
    def cancelar(self) -> None:
        if self._tarefa_extracao:
            self._tarefa_extracao.cancelar()

    @Slot(object)
    def _aoProgredir(self, fracao: float) -> None:
        self._progresso = fracao
        self.alterado.emit()

    @Slot(object)
    def _aoConcluir(self, saida) -> None:
        self._tarefa_extracao = None
        self._estado, self._progresso, self._saida = "concluido", 1.0, str(saida)
        self._mensagem = f"Áudio salvo como {Path(saida).name}"
        self.alterado.emit()

    @Slot(str)
    def _aoFalhar(self, mensagem: str) -> None:
        self._tarefa_extracao = None
        self._estado, self._mensagem = "erro", mensagem
        self.alterado.emit()

    @Slot()
    def _aoCancelar(self) -> None:
        self._tarefa_extracao = None
        self._estado, self._progresso, self._mensagem = "pronto", 0.0, ""
        self.alterado.emit()

    @Slot()
    def abrirPasta(self) -> None:
        if self._saida and Path(self._saida).exists():
            subprocess.Popen(["explorer", "/select,", self._saida])
        else:
            os.startfile(self._pasta)
