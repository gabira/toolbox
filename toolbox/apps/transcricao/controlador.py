"""Ponte entre a Tela.qml da Transcrição e o serviço (Whisper local)."""

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from toolbox.apps.transcricao import servico
from toolbox.nucleo import config
from toolbox.nucleo.arquivo import tamanho_legivel
from toolbox.nucleo.ffmpeg import sondar
from toolbox.nucleo.nomes import caminho_livre, limpar_nome
from toolbox.nucleo.tarefa import Tarefa

CHAVE_MODELO = "transcricao.modelo"
CHAVE_IDIOMA = "transcricao.idioma"
CHAVE_FORMATOS = "transcricao.formatos"
CHAVE_SEPARAR = "transcricao.separar"
FORMATOS = {"txt": "Texto (.txt)", "srt": "Legenda (.srt)", "docx": "Word (.docx)"}


def _duracao_legivel(segundos: float) -> str:
    """Ex.: "~40 min", "~1 h 20 min", "menos de 1 min"."""
    minutos = round(segundos / 60)
    if minutos < 1:
        return "menos de 1 min"
    horas, minutos = divmod(minutos, 60)
    return f"~{horas} h {minutos:02d} min" if horas else f"~{minutos} min"


class Controlador(QObject):
    alterado = Signal()
    alteradoProgresso = Signal()  # separado: não reavalia a tela inteira a cada trecho

    def __init__(self, pai=None):
        super().__init__(pai)
        self._modelo = config.ler(CHAVE_MODELO, "turbo")
        if self._modelo not in servico.MODELOS:
            self._modelo = "turbo"
        self._idioma = config.ler(CHAVE_IDIOMA, "pt")
        if self._idioma not in servico.IDIOMAS:
            self._idioma = "pt"
        salvos = config.ler(CHAVE_FORMATOS) or list(FORMATOS)
        self._formatos = [f for f in FORMATOS if f in salvos] or list(FORMATOS)
        self._separar = bool(config.ler(CHAVE_SEPARAR, True))
        self._arquivo = ""
        self._nome = ""
        self._pasta = ""           # padrão: a pasta do arquivo
        self._analise = {"estado": "vazio"}
        self._tarefa_analise = None
        self._tarefa = None
        self._estado = "pronto"    # pronto | trabalhando | concluido | erro
        self._fase = ""            # modelo | transcricao | salvando
        self._progresso = 0.0
        self._texto_progresso = ""
        self._texto = ""           # transcrição aparecendo ao vivo
        self._inicio = 0.0
        self._mensagem = ""
        self._saidas: list[str] = []
        self._modelo_em_uso = self._modelo

    # --- arquivo ---

    @Slot(str)
    def definirArquivo(self, caminho: str) -> None:
        if self._estado == "trabalhando" or caminho == self._arquivo:
            return
        self._arquivo = caminho
        self._nome = Path(caminho).stem if caminho else ""
        self._pasta = str(Path(caminho).parent) if caminho else ""
        if self._estado in ("concluido", "erro"):
            self._estado, self._mensagem, self._texto, self._saidas = "pronto", "", "", []
        self._tarefa_analise = None
        if not caminho:
            self._analise = {"estado": "vazio"}
        else:
            self._analise = {"estado": "analisando"}

            def analisar(_progresso, _cancelado):
                info = sondar(caminho)
                return {"duracao_s": info.duracao_s or 0, "tem_audio": bool(info.faixas_audio)}

            tarefa = Tarefa(analisar, self)
            tarefa.concluida.connect(self._aoAnalisar)
            tarefa.falhou.connect(self._aoFalharAnalise)
            self._tarefa_analise = tarefa
            tarefa.start()
        self.alterado.emit()

    @Slot(object)
    def _aoAnalisar(self, info) -> None:
        if self.sender() is not self._tarefa_analise:
            return
        self._tarefa_analise = None
        if not info["tem_audio"]:
            self._analise = {"estado": "erro", "mensagem": "Este arquivo não tem áudio."}
        else:
            self._analise = {"estado": "ok", "duracao_s": info["duracao_s"],
                             "duracao": servico.formatar_tempo(info["duracao_s"])}
        self.alterado.emit()

    @Slot(str)
    def _aoFalharAnalise(self, mensagem: str) -> None:
        if self.sender() is not self._tarefa_analise:
            return
        self._tarefa_analise = None
        self._analise = {"estado": "erro", "mensagem": f"Não foi possível ler o arquivo. {mensagem}"}
        self.alterado.emit()

    @Property("QVariantMap", notify=alterado)
    def analise(self) -> dict:
        return self._analise

    # --- opções ---

    @Property("QVariantList", notify=alterado)
    def modelos(self) -> list:
        duracao = self._analise.get("duracao_s") or 3600
        referencia = "este arquivo" if self._analise.get("duracao_s") else "1 h de áudio"
        vozes = self._separar and not servico.vozes_baixadas()
        return [{
            "id": m.id, "nome": m.nome,
            "baixado": servico.modelo_baixado(m.id) and not vozes,
            "descricao": f"{m.descricao} · {referencia} em "
                         f"{_duracao_legivel(servico.estimar_segundos(duracao, m.id, self._separar))}",
            "tamanho": tamanho_legivel(m.tamanho * (not servico.modelo_baixado(m.id))
                                       + servico.TAMANHO_VOZES * vozes),
            "selo": "Baixado" if servico.modelo_baixado(m.id) else m.selo,
        } for m in servico.MODELOS.values()]

    @Property(str, notify=alterado)
    def modelo(self) -> str:
        return self._modelo

    @Slot(str)
    def definirModelo(self, id_modelo: str) -> None:
        if id_modelo in servico.MODELOS and id_modelo != self._modelo:
            self._modelo = id_modelo
            config.gravar(CHAVE_MODELO, id_modelo)
            self.alterado.emit()

    @Property("QVariantList", constant=True)
    def idiomas(self) -> list:
        return [{"id": i, "nome": n} for i, n in servico.IDIOMAS.items()]

    @Property(str, notify=alterado)
    def idioma(self) -> str:
        return self._idioma

    @Slot(str)
    def definirIdioma(self, idioma: str) -> None:
        if idioma in servico.IDIOMAS and idioma != self._idioma:
            self._idioma = idioma
            config.gravar(CHAVE_IDIOMA, idioma)
            self.alterado.emit()

    @Property(bool, notify=alterado)
    def separar(self) -> bool:
        return self._separar

    @Slot(bool)
    def definirSeparar(self, separar: bool) -> None:
        if separar != self._separar:
            self._separar = separar
            config.gravar(CHAVE_SEPARAR, separar)
            self.alterado.emit()

    @Property("QVariantList", notify=alterado)
    def formatos(self) -> list:
        return [{"id": f, "nome": n, "marcado": f in self._formatos} for f, n in FORMATOS.items()]

    @Slot(str, bool)
    def marcarFormato(self, id_formato: str, marcado: bool) -> None:
        if id_formato not in FORMATOS:
            return
        if marcado and id_formato not in self._formatos:
            self._formatos.append(id_formato)
        elif not marcado and id_formato in self._formatos and len(self._formatos) > 1:
            self._formatos.remove(id_formato)  # pelo menos um formato fica marcado
        config.gravar(CHAVE_FORMATOS, self._formatos)
        self.alterado.emit()

    @Property(str, notify=alterado)
    def nomeSaida(self) -> str:
        return self._nome

    @Property(str, notify=alterado)
    def nomePadrao(self) -> str:
        return Path(self._arquivo).stem if self._arquivo else ""

    @Slot(str)
    def definirNome(self, nome: str) -> None:
        if nome != self._nome:
            self._nome = nome
            self.alterado.emit()

    @Property(str, notify=alterado)
    def pastaDestino(self) -> str:
        return self._pasta

    @Property(str, notify=alterado)
    def pastaDestinoUrl(self) -> str:
        return QUrl.fromLocalFile(self._pasta).toString() if self._pasta else ""

    @Slot(str)
    def definirPasta(self, url: str) -> None:
        pasta = QUrl(url).toLocalFile() or url
        if pasta and Path(pasta).is_dir():
            self._pasta = str(Path(pasta))
            self.alterado.emit()

    def _base(self) -> str:
        return limpar_nome(self._nome) or self.nomePadrao or "Transcrição"

    @Property(str, notify=alterado)
    def previsaoSaida(self) -> str:
        if not self._pasta or not Path(self._pasta).is_dir() or not self._arquivo:
            return ""
        return ", ".join(caminho_livre(Path(self._pasta), self._base(), f).name
                         for f in FORMATOS if f in self._formatos)

    # --- trabalho ---

    @Property(str, notify=alterado)
    def estado(self) -> str:
        return self._estado

    @Property(str, notify=alterado)
    def fase(self) -> str:
        return self._fase

    @Property(float, notify=alteradoProgresso)
    def progresso(self) -> float:
        return self._progresso

    @Property(str, notify=alteradoProgresso)
    def textoProgresso(self) -> str:
        return self._texto_progresso

    @Property(str, notify=alteradoProgresso)
    def texto(self) -> str:
        return self._texto

    @Property(str, notify=alterado)
    def mensagem(self) -> str:
        return self._mensagem

    @Property(bool, notify=alterado)
    def temDocumento(self) -> bool:
        return any(s.endswith(".docx") for s in self._saidas)

    @Slot()
    def transcrever(self) -> None:
        if self._estado == "trabalhando" or self._analise.get("estado") != "ok":
            return
        caminho, id_modelo, idioma, separar = self._arquivo, self._modelo, self._idioma, self._separar
        pasta, base, formatos = Path(self._pasta), self._base(), list(self._formatos)
        if not pasta.is_dir():
            self._estado, self._mensagem = "erro", "A pasta de destino não existe."
            self.alterado.emit()
            return
        modelo = servico.MODELOS[id_modelo]

        def trabalho(ao_progresso, cancelado):
            if not servico.modelo_baixado(id_modelo):
                ao_progresso({"fase": "modelo"})
                servico.baixar_modelo(id_modelo, lambda p: ao_progresso({"fase": "modelo", **p}), cancelado)
            if separar and not servico.vozes_baixadas():
                ao_progresso({"fase": "modelo"})
                servico.baixar_vozes(lambda p: ao_progresso({"fase": "modelo", **p}), cancelado)
            ao_progresso({"fase": "transcricao"})
            resultado = servico.transcrever(
                caminho, id_modelo, idioma, separar,
                lambda p: ao_progresso({"fase": "transcricao" if p["etapa"] == "texto" else "vozes", **p}),
                cancelado)
            ao_progresso({"fase": "salvando"})
            detalhes = (f"Transcrição de {Path(caminho).name} · {servico.formatar_tempo(resultado.duracao)} · "
                        f"{modelo.descricao} · {datetime.now():%d/%m/%Y %H:%M}")
            saidas = []
            for formato in FORMATOS:
                if formato not in formatos:
                    continue
                destino = caminho_livre(pasta, base, formato)
                if formato == "txt":
                    servico.salvar_txt(resultado, destino)
                elif formato == "srt":
                    servico.salvar_srt(resultado, destino)
                else:
                    servico.salvar_docx(resultado, destino, Path(caminho).stem, detalhes)
                saidas.append(str(destino))
            return {"saidas": saidas, "texto": servico.texto_corrido(resultado).strip()}

        self._modelo_em_uso = id_modelo
        self._estado, self._fase, self._progresso = "trabalhando", "", 0.0
        self._texto_progresso, self._texto, self._mensagem, self._saidas = "Preparando…", "", "", []
        tarefa = Tarefa(trabalho, self)
        tarefa.progresso.connect(self._aoProgredir)
        tarefa.concluida.connect(self._aoConcluir)
        tarefa.falhou.connect(self._aoFalhar)
        tarefa.cancelada.connect(self._aoCancelar)
        self._tarefa = tarefa
        tarefa.start()
        self.alterado.emit()
        self.alteradoProgresso.emit()

    @Slot(object)
    def _aoProgredir(self, evento) -> None:
        fase = evento.get("fase", self._fase)
        if fase != self._fase:
            self._fase, self._progresso, self._inicio = fase, 0.0, time.monotonic()
            self._texto_progresso = {"modelo": "Baixando o modelo (só na 1ª vez)…",
                                     "transcricao": "Carregando o modelo…",
                                     "vozes": "Identificando quem fala…",
                                     "salvando": "Salvando os arquivos…"}.get(fase, "")
            self.alterado.emit()
        if fase == "modelo" and "fracao" in evento:
            self._progresso = evento["fracao"]
            self._texto_progresso = f"Baixando o modelo (só na 1ª vez) · {evento['texto']}"
        elif fase == "transcricao" and "fracao" in evento:
            self._progresso = evento["fracao"]
            decorrido = time.monotonic() - self._inicio
            if evento["fracao"] > 0.02:
                restante = decorrido * (1 - evento["fracao"]) / evento["fracao"]
            else:  # antes do 1º trecho: estimativa pela velocidade medida do modelo
                restante = servico.estimar_segundos(evento["duracao"], self._modelo_em_uso) - decorrido
            if self._separar:  # ainda falta separar as vozes depois do texto
                restante += evento["duracao"] / servico.VELOCIDADE_VOZES
            self._texto_progresso = (
                f"Transcrevendo · {servico.formatar_tempo(evento['segundo'])} de "
                f"{servico.formatar_tempo(evento['duracao'])} · faltam {_duracao_legivel(max(0, restante))}")
            self._texto = (self._texto + " " + evento["texto"]).strip()
        elif fase == "vozes" and "fracao" in evento:
            self._progresso = evento["fracao"]
            self._texto_progresso = f"Identificando quem fala · {evento['fracao']:.0%}"
        self.alteradoProgresso.emit()

    @Slot(object)
    def _aoConcluir(self, resultado) -> None:
        self._tarefa = None
        self._estado, self._progresso, self._saidas = "concluido", 1.0, resultado["saidas"]
        self._texto = resultado["texto"]  # versão final, com "Pessoa 1:", "Pessoa 2:"… quando houver
        nomes = ", ".join(Path(s).name for s in self._saidas)
        self._mensagem = f"Transcrição salva: {nomes}"
        self.alterado.emit()
        self.alteradoProgresso.emit()

    @Slot(str)
    def _aoFalhar(self, mensagem: str) -> None:
        self._tarefa = None
        self._estado, self._mensagem = "erro", mensagem
        self.alterado.emit()

    @Slot()
    def _aoCancelar(self) -> None:
        self._tarefa = None
        self._estado, self._progresso, self._mensagem, self._fase = "pronto", 0.0, "", ""
        self.alterado.emit()
        self.alteradoProgresso.emit()

    @Slot()
    def cancelar(self) -> None:
        if self._tarefa:
            self._tarefa.cancelar()
            self._texto_progresso = "Cancelando…"
            self.alteradoProgresso.emit()

    @Slot()
    def abrirDocumento(self) -> None:
        documento = next((s for s in self._saidas if s.endswith(".docx")), "")
        if documento and Path(documento).exists():
            os.startfile(documento)

    @Slot()
    def abrirPasta(self) -> None:
        if self._saidas and Path(self._saidas[0]).exists():
            subprocess.Popen(["explorer", "/select,", self._saidas[0]])
        elif self._pasta:
            os.startfile(self._pasta)
