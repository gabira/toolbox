"""Ponte entre a Tela.qml do Para PDF e o serviço de conversão."""

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from toolbox.apps.para_pdf import servico
from toolbox.nucleo import arquivo, config
from toolbox.nucleo.nomes import caminho_livre, limpar_nome
from toolbox.nucleo.tarefa import Tarefa

CHAVE_PAGINA = "para_pdf.pagina"


class Controlador(QObject):
    alterado = Signal()

    def __init__(self, pai=None):
        super().__init__(pai)
        self._arquivo = ""
        self._tipo = ""
        self._analise: dict = {"estado": "vazio"}
        self._imagens: list[str] = []    # só para imagens: páginas do PDF, na ordem
        self._dimensoes: dict = {}       # cache de largura × altura por caminho
        self._pagina = config.ler(CHAVE_PAGINA, servico.PAGINA_IMAGEM)
        self._nome = ""
        self._pasta = ""                 # padrão: a pasta do arquivo original
        self._estado = "pronto"          # pronto | convertendo | concluido | erro
        self._progresso = 0.0
        self._mensagem = ""
        self._saida = ""
        self._tarefa = None

    # ------------------------------------------------------------ análise

    @Slot(str)
    def analisar(self, caminho: str) -> None:
        if self._estado == "convertendo":
            return
        if caminho != self._arquivo:
            self._arquivo = caminho
            self._tipo = arquivo.detectar_tipo(caminho) if caminho else ""
            self._nome = Path(caminho).stem if caminho else ""
            self._pasta = str(Path(caminho).parent) if caminho else ""
            self._imagens = [caminho] if servico.categoria(self._tipo) == "imagem" else []
        if self._estado in ("concluido", "erro"):
            self._estado, self._mensagem = "pronto", ""

        cat = servico.categoria(self._tipo)
        escolhido = servico.motor(cat)
        if not caminho:
            self._analise = {"estado": "vazio"}
        elif cat is None:
            self._analise = {"estado": "erro", "mensagem": "Este tipo de arquivo não pode ser convertido em PDF."}
        elif escolhido is None:
            programa = servico.PROGRAMAS_OFFICE.get(cat, "programa")
            self._analise = {"estado": "erro",
                             "mensagem": f"Para converter é preciso ter o {programa} ou o LibreOffice instalado."}
        else:
            self._analise = {
                "estado": "ok",
                "categoria": cat,
                "nomeCategoria": servico.NOMES_CATEGORIA[cat],
                "motor": escolhido[1],
                "demorado": escolhido[0] in ("office", "libreoffice"),
            }
        self.alterado.emit()

    @Property("QVariantMap", notify=alterado)
    def analise(self) -> dict:
        return self._analise

    # ------------------------------------------------------------ imagens (páginas)

    @Property("QVariantList", notify=alterado)
    def imagens(self) -> list:
        lista = []
        for caminho in self._imagens:
            if caminho not in self._dimensoes:
                self._dimensoes[caminho] = servico.dimensoes_imagem(caminho)
            tamanho = self._dimensoes[caminho]
            lista.append({
                "caminho": caminho,
                "url": QUrl.fromLocalFile(caminho).toString(),
                "nome": Path(caminho).name,
                "detalhe": f"{tamanho[0]} × {tamanho[1]}" if tamanho else "",
            })
        return lista

    @Slot("QVariantList")
    def adicionarImagens(self, urls: list) -> None:
        for url in urls:
            caminho = QUrl(str(url)).toLocalFile() or str(url)
            if Path(caminho).is_file() and servico.categoria(arquivo.detectar_tipo(caminho)) == "imagem":
                self._imagens.append(str(Path(caminho)))
        self.alterado.emit()

    @Slot(int)
    def removerImagem(self, indice: int) -> None:
        if 0 <= indice < len(self._imagens) and len(self._imagens) > 1:
            del self._imagens[indice]
            self.alterado.emit()

    @Slot(int, int)
    def moverImagem(self, indice: int, direcao: int) -> None:
        destino = indice + direcao
        if 0 <= indice < len(self._imagens) and 0 <= destino < len(self._imagens):
            self._imagens[indice], self._imagens[destino] = self._imagens[destino], self._imagens[indice]
            self.alterado.emit()

    @Property(str, notify=alterado)
    def pagina(self) -> str:
        return self._pagina

    @Slot(str)
    def definirPagina(self, pagina: str) -> None:
        if pagina in (servico.PAGINA_IMAGEM, servico.PAGINA_A4):
            self._pagina = pagina
            config.gravar(CHAVE_PAGINA, pagina)
            self.alterado.emit()

    # ------------------------------------------------------------ saída

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

    def _caminho_saida(self) -> Path | None:
        if not self._pasta or not Path(self._pasta).is_dir():
            return None
        base = limpar_nome(self._nome, "pdf") or self.nomePadrao
        return caminho_livre(Path(self._pasta), base, "pdf")

    @Property(str, notify=alterado)
    def previsaoSaida(self) -> str:
        saida = self._caminho_saida()
        return saida.name if saida and self._analise.get("estado") == "ok" else ""

    # ------------------------------------------------------------ conversão

    @Property(str, notify=alterado)
    def estado(self) -> str:
        return self._estado

    @Property(float, notify=alterado)
    def progresso(self) -> float:
        return self._progresso

    @Property(str, notify=alterado)
    def mensagem(self) -> str:
        return self._mensagem

    @Slot()
    def converter(self) -> None:
        if self._estado == "convertendo" or self._analise.get("estado") != "ok":
            return
        saida = self._caminho_saida()
        if saida is None:
            self._estado, self._mensagem = "erro", "A pasta de destino não existe."
            self.alterado.emit()
            return
        entradas = list(self._imagens) if self._imagens else [self._arquivo]
        tipo, pagina = self._tipo, self._pagina
        self._estado, self._progresso, self._mensagem, self._saida = "convertendo", 0.0, "", ""

        tarefa = Tarefa(lambda ao_progresso, cancelado: servico.converter(
            entradas, tipo, saida, pagina, ao_progresso, cancelado), self)
        tarefa.progresso.connect(self._aoProgredir)
        tarefa.concluida.connect(self._aoConcluir)
        tarefa.falhou.connect(self._aoFalhar)
        tarefa.cancelada.connect(self._aoCancelar)
        self._tarefa = tarefa
        tarefa.start()
        self.alterado.emit()

    @Slot()
    def cancelar(self) -> None:
        if self._tarefa:
            self._tarefa.cancelar()

    @Slot(object)
    def _aoProgredir(self, fracao) -> None:
        self._progresso = float(fracao)
        self.alterado.emit()

    @Slot(object)
    def _aoConcluir(self, saida) -> None:
        self._tarefa = None
        self._estado, self._progresso, self._saida = "concluido", 1.0, str(saida)
        self._mensagem = f"PDF salvo como {Path(saida).name}"
        self.alterado.emit()

    @Slot(str)
    def _aoFalhar(self, mensagem: str) -> None:
        self._tarefa = None
        self._estado, self._mensagem = "erro", mensagem
        self.alterado.emit()

    @Slot()
    def _aoCancelar(self) -> None:
        self._tarefa = None
        self._estado, self._progresso, self._mensagem = "pronto", 0.0, ""
        self.alterado.emit()

    @Property(str, notify=alterado)
    def arquivoSaida(self) -> str:
        return self._saida

    @Slot()
    def abrirPdf(self) -> None:
        if self._saida and Path(self._saida).exists():
            os.startfile(self._saida)

    @Slot()
    def abrirPasta(self) -> None:
        if self._saida and Path(self._saida).exists():
            subprocess.Popen(["explorer", "/select,", self._saida])
        elif self._pasta:
            os.startfile(self._pasta)
