"""Ponte entre a Tela.qml do baixador e o serviço do yt-dlp."""

import json
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import (Property, QAbstractListModel, QModelIndex, QObject, Qt, QUrl,
                            Signal, Slot)

from toolbox.apps.baixador_youtube import servico
from toolbox.nucleo import config
from toolbox.nucleo.ffmpeg import SEM_JANELA
from toolbox.nucleo.tarefa import Tarefa

CHAVE_PASTA = "baixador_youtube.pasta"
CHAVE_QUALIDADE_LOTE = "baixador_youtube.qualidade_lote"
CONFIG_ANTIGO = Path.home() / ".yt_downloader.json"  # preferências do app download_yt

NOMES_LOTE = {
    servico.MELHOR: ("Melhor disponível", "Sem limite de resolução"),
    "1080": ("1080p", "Full HD ou menos"),
    "720": ("720p", "HD ou menos"),
    "480": ("480p", "ou menos"),
    "360": ("360p", "ou menos"),
    servico.AUDIO: ("Apenas áudio", "MP3 320 kb/s"),
}


def _pasta_inicial() -> str:
    if pasta := config.ler(CHAVE_PASTA):
        return pasta
    try:  # reaproveita a pasta que o usuário já usava no download_yt
        antiga = json.loads(CONFIG_ANTIGO.read_text(encoding="utf-8")).get("pasta", "")
        if antiga and Path(antiga).is_dir():
            return antiga
    except (OSError, ValueError, AttributeError):
        pass
    return str(config.pasta_downloads())


class ModeloFila(QAbstractListModel):
    """Itens da fila de vários links. Atualiza linha a linha, sem recriar a lista."""

    PAPEIS = {Qt.UserRole + 1: b"link", Qt.UserRole + 2: b"titulo", Qt.UserRole + 3: b"estado",
              Qt.UserRole + 4: b"tom", Qt.UserRole + 5: b"progresso"}
    _CHAVES = {nome.decode(): papel for papel, nome in PAPEIS.items()}

    def __init__(self, pai=None):
        super().__init__(pai)
        self._itens: list[dict] = []

    def rowCount(self, _pai=QModelIndex()) -> int:
        return len(self._itens)

    def data(self, indice, papel=Qt.DisplayRole):
        if not indice.isValid() or papel not in self.PAPEIS:
            return None
        return self._itens[indice.row()][self.PAPEIS[papel].decode()]

    def roleNames(self):
        return self.PAPEIS

    def redefinir(self, links: list[str]) -> None:
        self.beginResetModel()
        self._itens = [{"link": l, "titulo": "", "estado": "na fila", "tom": "normal", "progresso": -1.0}
                       for l in links]
        self.endResetModel()

    def atualizar(self, i: int, **campos) -> None:
        if 0 <= i < len(self._itens):
            self._itens[i].update(campos)
            indice = self.index(i)
            self.dataChanged.emit(indice, indice, [self._CHAVES[c] for c in campos])


class Controlador(QObject):
    alterado = Signal()
    alteradoProgresso = Signal()  # separado para não reavaliar a tela inteira a cada tique

    def __init__(self, pai=None):
        super().__init__(pai)
        self._aba = "unico"
        self._pasta = _pasta_inicial()
        self._tarefa = None           # só um trabalho por vez (análise, download ou fila)
        self._tarefa_motor = None

        # --- um vídeo ---
        self._link = ""
        self._estado = "vazio"        # vazio | analisando | pronto | baixando | concluido | erro
        self._info: dict = {}
        self._qualidade = ""
        self._playlist = True
        self._mensagem = ""
        self._arquivo_baixado = ""

        # --- vários vídeos ---
        self._texto_links = ""
        self._qualidade_lote = config.ler(CHAVE_QUALIDADE_LOTE, "1080")
        if self._qualidade_lote not in NOMES_LOTE:
            self._qualidade_lote = "1080"
        self._fila = ModeloFila(self)
        self._estado_lote = "parado"  # parado | rodando
        self._status_lote = ""
        self._tom_status_lote = "normal"

        # --- progresso (compartilhado pelos dois modos) ---
        self._progresso = 0.0
        self._texto_progresso = ""

        self._mensagem_motor = ""

    # ------------------------------------------------------------ gerais

    @Property(str, notify=alterado)
    def aba(self) -> str:
        return self._aba

    @Slot(str)
    def definirAba(self, aba: str) -> None:
        if aba in ("unico", "lote") and aba != self._aba:
            self._aba = aba
            self.alterado.emit()

    @Property(bool, notify=alterado)
    def ocupado(self) -> bool:
        return self._tarefa is not None

    @Property(str, notify=alterado)
    def pastaDestino(self) -> str:
        return self._pasta

    @Property(str, notify=alterado)
    def pastaDestinoUrl(self) -> str:
        return QUrl.fromLocalFile(self._pasta).toString()

    @Slot(str)
    def definirPasta(self, url: str) -> None:
        pasta = QUrl(url).toLocalFile() or url
        if pasta and Path(pasta).is_dir():
            self._pasta = str(Path(pasta))
            config.gravar(CHAVE_PASTA, self._pasta)
            self.alterado.emit()

    @Slot()
    def abrirPasta(self) -> None:
        if self._arquivo_baixado and Path(self._arquivo_baixado).exists():
            subprocess.Popen(["explorer", "/select,", self._arquivo_baixado])
        else:
            os.startfile(self._pasta)

    @Property(float, notify=alteradoProgresso)
    def progresso(self) -> float:
        return self._progresso

    @Property(str, notify=alteradoProgresso)
    def textoProgresso(self) -> str:
        return self._texto_progresso

    @Slot()
    def cancelar(self) -> None:
        if self._tarefa:
            self._tarefa.cancelar()
            self._texto_progresso = "Parando…"
            self.alteradoProgresso.emit()

    def _iniciar(self, funcao, concluida, falhou, cancelada, progresso=None) -> None:
        tarefa = Tarefa(funcao, self)
        tarefa.concluida.connect(concluida)
        tarefa.falhou.connect(falhou)
        tarefa.cancelada.connect(cancelada)
        if progresso:
            tarefa.progresso.connect(progresso)
        self._tarefa = tarefa
        self._progresso, self._texto_progresso = 0.0, ""
        tarefa.start()
        self.alteradoProgresso.emit()

    def _liberar(self) -> None:
        self._tarefa = None

    # ------------------------------------------------------------ um vídeo

    @Property(str, notify=alterado)
    def link(self) -> str:
        return self._link

    @Slot(str)
    def definirLink(self, link: str) -> None:
        self._link = link

    @Property(str, notify=alterado)
    def estado(self) -> str:
        return self._estado

    @Property("QVariantMap", notify=alterado)
    def info(self) -> dict:
        return self._info

    @Property("QVariantList", notify=alterado)
    def opcoesQualidade(self) -> list:
        return servico.opcoes_qualidade(self._info.get("alturas", [])) if self._info else []

    @Property(str, notify=alterado)
    def qualidade(self) -> str:
        return self._qualidade

    @Slot(str)
    def definirQualidade(self, qualidade: str) -> None:
        self._qualidade = qualidade
        self.alterado.emit()

    @Property(bool, notify=alterado)
    def baixarPlaylist(self) -> bool:
        return self._playlist

    @Slot(bool)
    def definirPlaylist(self, valor: bool) -> None:
        self._playlist = valor
        self.alterado.emit()

    @Property(str, notify=alterado)
    def mensagem(self) -> str:
        return self._mensagem

    @Property(str, notify=alterado)
    def arquivoBaixado(self) -> str:
        """Arquivo único baixado (vazio para playlists) — pode virar o arquivo da TOOLBOX."""
        return self._arquivo_baixado

    @Slot()
    def analisarLink(self) -> None:
        if self._tarefa:
            return
        link = self._link.strip()
        if not link:
            self._estado, self._mensagem = "erro", "Cole o link do vídeo primeiro."
            self.alterado.emit()
            return
        self._estado, self._info, self._mensagem, self._arquivo_baixado = "analisando", {}, "", ""
        self._iniciar(lambda _p, _c: servico.analisar(link),
                      self._aoAnalisar, self._aoFalharUnico, self._aoCancelarUnico)
        self.alterado.emit()

    @Slot(object)
    def _aoAnalisar(self, info) -> None:
        self._liberar()
        self._info = info
        self._qualidade = str(info["alturas"][0])
        self._playlist = True
        self._estado = "pronto"
        self.alterado.emit()

    @Slot()
    def baixarUnico(self) -> None:
        if self._tarefa or self._estado not in ("pronto", "concluido", "erro") or not self._info:
            return
        link, qualidade, pasta = self._link.strip(), self._qualidade, self._pasta
        playlist = self._info.get("e_playlist", False) and self._playlist
        self._estado, self._mensagem, self._arquivo_baixado = "baixando", "", ""
        self._iniciar(
            lambda ao_progresso, cancelado: servico.baixar(link, qualidade, pasta, playlist,
                                                           ao_progresso, cancelado),
            self._aoBaixar, self._aoFalharUnico, self._aoCancelarUnico, self._aoProgredir,
        )
        self._texto_progresso = "Iniciando…"
        self.alterado.emit()

    @Slot(object)
    def _aoProgredir(self, evento) -> None:
        if evento.get("fracao") is not None:
            self._progresso = evento["fracao"]
        self._texto_progresso = evento.get("texto", "")
        self.alteradoProgresso.emit()

    @Slot(object)
    def _aoBaixar(self, arquivos) -> None:
        self._liberar()
        self._estado, self._progresso = "concluido", 1.0
        if len(arquivos) == 1:
            self._arquivo_baixado = str(arquivos[0])
            self._mensagem = f"Salvo como {arquivos[0].name}"
        else:
            self._mensagem = f"{len(arquivos)} arquivos salvos em {self._pasta}"
        self.alterado.emit()
        self.alteradoProgresso.emit()

    @Slot(str)
    def _aoFalharUnico(self, mensagem: str) -> None:
        self._liberar()
        # Falha no download mantém as informações do vídeo para tentar de novo.
        self._estado, self._mensagem = "erro", mensagem
        self.alterado.emit()

    @Slot()
    def _aoCancelarUnico(self) -> None:
        self._liberar()
        self._estado = "pronto" if self._info else "vazio"
        self._mensagem, self._progresso, self._texto_progresso = "Download cancelado.", 0.0, ""
        self.alterado.emit()
        self.alteradoProgresso.emit()

    # ------------------------------------------------------------ vários vídeos

    @Property(str, notify=alterado)
    def textoLinks(self) -> str:
        return self._texto_links

    @Slot(str)
    def definirTextoLinks(self, texto: str) -> None:
        antes = self.totalLinks
        self._texto_links = texto
        if self.totalLinks != antes:
            self.alterado.emit()

    @Property(int, notify=alterado)
    def totalLinks(self) -> int:
        return len(servico.extrair_links(self._texto_links))

    @Property("QVariantList", constant=True)
    def opcoesLote(self) -> list:
        return [{"id": id_, "nome": nome, "descricao": desc} for id_, (nome, desc) in NOMES_LOTE.items()]

    @Property(str, notify=alterado)
    def qualidadeLote(self) -> str:
        return self._qualidade_lote

    @Slot(str)
    def definirQualidadeLote(self, qualidade: str) -> None:
        if qualidade in NOMES_LOTE:
            self._qualidade_lote = qualidade
            config.gravar(CHAVE_QUALIDADE_LOTE, qualidade)
            self.alterado.emit()

    @Property(QObject, constant=True)
    def fila(self) -> QObject:
        return self._fila

    @Property(str, notify=alterado)
    def estadoLote(self) -> str:
        return self._estado_lote

    @Property(str, notify=alterado)
    def statusLote(self) -> str:
        return self._status_lote

    @Property(str, notify=alterado)
    def tomStatusLote(self) -> str:
        return self._tom_status_lote

    @Slot(bool)
    def iniciarLote(self, so_conferir: bool) -> None:
        if self._tarefa:
            return
        links = servico.extrair_links(self._texto_links)
        if not links:
            self._status_lote, self._tom_status_lote = "Cole pelo menos um link.", "erro"
            self.alterado.emit()
            return
        qualidade, pasta = self._qualidade_lote, self._pasta
        self._fila.redefinir(links)
        self._estado_lote, self._status_lote, self._tom_status_lote = "rodando", "Começando…", "normal"
        self._iniciar(
            lambda ao_evento, cancelado: servico.processar_lote(
                links, qualidade, pasta, so_conferir, ao_evento, cancelado),
            self._aoTerminarLote, self._aoFalharLote, self._aoCancelarLote, self._aoEventoLote,
        )
        self.alterado.emit()

    @Slot(object)
    def _aoEventoLote(self, evento) -> None:
        tipo, i = evento["tipo"], evento.get("i", -1)
        if tipo == "item":
            self._fila.atualizar(i, estado=evento["estado"], tom=evento["tom"],
                                 progresso=-1.0 if evento["tom"] != "sucesso" else 1.0)
        elif tipo == "titulo":
            self._fila.atualizar(i, titulo=evento["titulo"])
        elif tipo == "progresso":
            if evento.get("fracao") is not None:
                self._progresso = evento["fracao"]
                self._fila.atualizar(i, progresso=evento["fracao"])
            self._texto_progresso = evento.get("texto", "")
            self.alteradoProgresso.emit()
        elif tipo == "geral":
            self._status_lote = evento["texto"]
            self.alterado.emit()

    @Slot(object)
    def _aoTerminarLote(self, resultado) -> None:
        self._liberar()
        ok, falhas = resultado["ok"], resultado["falhas"]
        verbo = "conferidos" if resultado["so_conferir"] else "baixados"
        if resultado["cancelado"]:
            self._status_lote, self._tom_status_lote = f"Parado. {ok} {verbo} antes de parar.", "aviso"
        elif falhas == 0:
            self._status_lote, self._tom_status_lote = f"{ok} {verbo} com sucesso.", "sucesso"
        else:
            self._status_lote = f"{ok} {verbo}, {falhas} com erro — veja a fila abaixo."
            self._tom_status_lote = "aviso"
        self._estado_lote, self._texto_progresso = "parado", ""
        self.alterado.emit()
        self.alteradoProgresso.emit()

    @Slot(str)
    def _aoFalharLote(self, mensagem: str) -> None:
        self._liberar()
        self._estado_lote, self._status_lote, self._tom_status_lote = "parado", mensagem, "erro"
        self.alterado.emit()

    @Slot()
    def _aoCancelarLote(self) -> None:
        # processar_lote trata o cancelamento sozinho; isto só cobre um cancelamento fora do laço.
        self._aoFalharLote("Fila interrompida.")

    # ------------------------------------------------------------ motor (yt-dlp)

    @Property(str, notify=alterado)
    def versaoMotor(self) -> str:
        from yt_dlp.version import __version__
        return __version__

    @Property(str, notify=alterado)
    def mensagemMotor(self) -> str:
        return self._mensagem_motor

    @Property(bool, notify=alterado)
    def atualizandoMotor(self) -> bool:
        return self._tarefa_motor is not None

    @Slot()
    def atualizarMotor(self) -> None:
        """O YouTube muda o site com frequência; atualizar o yt-dlp costuma resolver."""
        if self._tarefa_motor:
            return

        def atualizar(_p, _c):
            comando = [sys.executable, "-m", "pip", "install", "-U", "-q",
                       "--disable-pip-version-check", "yt-dlp"]
            resultado = subprocess.run(comando, capture_output=True, text=True, creationflags=SEM_JANELA)
            if resultado.returncode != 0:
                raise RuntimeError("Não foi possível atualizar. Verifique a internet.")
            versao = subprocess.run(
                [sys.executable, "-c", "import yt_dlp.version as v; print(v.__version__)"],
                capture_output=True, text=True, creationflags=SEM_JANELA,
            ).stdout.strip()
            return versao

        self._tarefa_motor = Tarefa(atualizar, self)
        self._tarefa_motor.concluida.connect(self._aoAtualizarMotor)
        self._tarefa_motor.falhou.connect(self._aoFalharMotor)
        self._mensagem_motor = "Atualizando…"
        self._tarefa_motor.start()
        self.alterado.emit()

    @Slot(object)
    def _aoAtualizarMotor(self, versao) -> None:
        self._tarefa_motor = None
        if versao and versao != self.versaoMotor:
            self._mensagem_motor = f"Atualizado para {versao}. Feche e abra a TOOLBOX para usar."
        else:
            self._mensagem_motor = "Já está na versão mais recente."
        self.alterado.emit()

    @Slot(str)
    def _aoFalharMotor(self, mensagem: str) -> None:
        self._tarefa_motor = None
        self._mensagem_motor = mensagem
        self.alterado.emit()
