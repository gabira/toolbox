"""Ponte entre a Tela.qml do Compactador e o serviço (PyMuPDF + Pillow)."""

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import (Property, QAbstractListModel, QModelIndex, QObject, Qt, QUrl,
                            Signal, Slot)

from toolbox.apps.compactador import servico
from toolbox.nucleo import arquivo, config
from toolbox.nucleo.tarefa import Tarefa

CHAVE_NIVEL = "compactador.nivel"


def _reducao(antes: int, depois: int) -> str:
    return f"−{round((1 - depois / antes) * 100)}%" if antes else ""


class ModeloFila(QAbstractListModel):
    """Arquivos da fila. Atualiza linha a linha, sem recriar a lista."""

    PAPEIS = {Qt.UserRole + 1: b"nome", Qt.UserRole + 2: b"detalhe", Qt.UserRole + 3: b"estado",
              Qt.UserRole + 4: b"tom", Qt.UserRole + 5: b"progresso", Qt.UserRole + 6: b"miniatura"}
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

    def itens(self) -> list[dict]:
        return self._itens

    def adicionar(self, item: dict) -> None:
        self.beginInsertRows(QModelIndex(), len(self._itens), len(self._itens))
        self._itens.append(item)
        self.endInsertRows()

    def remover(self, i: int) -> None:
        if 0 <= i < len(self._itens):
            self.beginRemoveRows(QModelIndex(), i, i)
            del self._itens[i]
            self.endRemoveRows()

    def limpar(self) -> None:
        self.beginResetModel()
        self._itens = []
        self.endResetModel()

    def atualizar(self, i: int, **campos) -> None:
        if 0 <= i < len(self._itens):
            self._itens[i].update(campos)
            indice = self.index(i)
            self.dataChanged.emit(indice, indice, [self._CHAVES[c] for c in campos if c in self._CHAVES])


class Controlador(QObject):
    alterado = Signal()
    alteradoProgresso = Signal()  # separado para não reavaliar a tela inteira a cada passo

    def __init__(self, pai=None):
        super().__init__(pai)
        self._nivel = config.ler(CHAVE_NIVEL, "equilibrado")
        if self._nivel not in servico.NIVEIS:
            self._nivel = "equilibrado"
        self._fila = ModeloFila(self)
        self._pasta = ""               # "" = cada cópia ao lado do seu original
        self._estado = "pronto"        # pronto | compactando | concluido
        self._progresso = 0.0
        self._mensagem = ""
        self._tom_mensagem = "normal"
        self._saidas: list[str] = []
        self._tarefa = None

    # ------------------------------------------------------------ fila

    @Property(QObject, constant=True)
    def fila(self) -> QObject:
        return self._fila

    @Property(int, notify=alterado)
    def total(self) -> int:
        return self._fila.rowCount()

    @Property(str, notify=alterado)
    def resumoFila(self) -> str:
        itens = self._fila.itens()
        if not itens:
            return ""
        tamanho = arquivo.tamanho_legivel(sum(i["tamanho"] for i in itens))
        return f"{len(itens)} arquivo{'s' if len(itens) > 1 else ''} · {tamanho}"

    def _novo_item(self, caminho: str) -> dict | None:
        tipo = arquivo.detectar_tipo(caminho)
        if tipo not in servico.TIPOS_ACEITOS:
            return None
        tamanho = Path(caminho).stat().st_size
        e_imagem = tipo != "application/pdf"
        return {"caminho": caminho, "tipo": tipo, "tamanho": tamanho, "nome": Path(caminho).name,
                "detalhe": f"{arquivo.descrever_tipo(tipo)} · {arquivo.tamanho_legivel(tamanho)}",
                "estado": "", "tom": "normal", "progresso": -1.0,
                "miniatura": QUrl.fromLocalFile(caminho).toString() if e_imagem else ""}

    def _recomecar_se_concluido(self) -> None:
        """Depois de terminar, arquivos novos começam uma fila nova."""
        if self._estado == "concluido":
            self._fila.limpar()
            self._estado, self._mensagem, self._saidas = "pronto", "", []
            self._progresso = 0.0
            self.alteradoProgresso.emit()

    def _adicionar(self, caminhos: list[str]) -> int:
        """Devolve quantos não entraram (tipo não aceito)."""
        existentes = {os.path.normcase(i["caminho"]) for i in self._fila.itens()}
        recusados = 0
        for caminho in caminhos:
            caminho = str(Path(caminho))
            if os.path.normcase(caminho) in existentes or not Path(caminho).is_file():
                continue
            item = self._novo_item(caminho)
            if item is None:
                recusados += 1
                continue
            existentes.add(os.path.normcase(caminho))
            self._fila.adicionar(item)
        return recusados

    @Slot(str)
    def receberArquivo(self, caminho: str) -> None:
        """Arquivo da entrada compartilhada (centro da TOOLBOX)."""
        if not caminho or self._tarefa:
            return
        if self._estado == "concluido" and any(os.path.normcase(i["caminho"]) == os.path.normcase(caminho)
                                               for i in self._fila.itens()):
            return  # voltou para o app com o mesmo arquivo: mantém o resultado na tela
        self._recomecar_se_concluido()
        self._adicionar([caminho])
        self.alterado.emit()

    @Slot("QVariantList")
    def adicionarArquivos(self, urls: list) -> None:
        if self._tarefa:
            return
        self._recomecar_se_concluido()
        recusados = self._adicionar([QUrl(str(u)).toLocalFile() or str(u) for u in urls])
        if recusados:
            self._mensagem = (f"{recusados} arquivo{'s' if recusados > 1 else ''} ignorado"
                              f"{'s' if recusados > 1 else ''}: só PDF, JPG, PNG e WebP.")
            self._tom_mensagem = "aviso"
        elif self._estado == "pronto":
            self._mensagem = ""
        self.alterado.emit()

    @Slot(int)
    def remover(self, i: int) -> None:
        if not self._tarefa:
            self._fila.remover(i)
            self.alterado.emit()

    @Slot()
    def limpar(self) -> None:
        if not self._tarefa:
            self._fila.limpar()
            self._estado, self._mensagem, self._saidas, self._progresso = "pronto", "", [], 0.0
            self.alterado.emit()
            self.alteradoProgresso.emit()

    # ------------------------------------------------------------ opções

    @Property("QVariantList", constant=True)
    def niveis(self) -> list:
        return [{"id": n.id, "nome": n.nome, "descricao": n.descricao} for n in servico.NIVEIS.values()]

    @Property(str, notify=alterado)
    def nivel(self) -> str:
        return self._nivel

    @Slot(str)
    def definirNivel(self, nivel: str) -> None:
        if nivel in servico.NIVEIS and nivel != self._nivel and not self._tarefa:
            self._nivel = nivel
            config.gravar(CHAVE_NIVEL, nivel)
            if self._estado == "concluido":  # quer testar outro nível: a mesma fila volta a esperar
                self._estado, self._mensagem, self._saidas = "pronto", "", []
                for i in range(self._fila.rowCount()):
                    self._fila.atualizar(i, estado="", tom="normal", progresso=-1.0)
            self.alterado.emit()

    @Property(str, notify=alterado)
    def pastaDestino(self) -> str:
        return self._pasta

    @Property(str, notify=alterado)
    def pastaDestinoUrl(self) -> str:
        if self._pasta:
            return QUrl.fromLocalFile(self._pasta).toString()
        itens = self._fila.itens()
        return QUrl.fromLocalFile(str(Path(itens[0]["caminho"]).parent)).toString() if itens else ""

    @Slot(str)
    def definirPasta(self, url: str) -> None:
        pasta = QUrl(url).toLocalFile() or url
        if not pasta or Path(pasta).is_dir():
            self._pasta = str(Path(pasta)) if pasta else ""
            self.alterado.emit()

    # ------------------------------------------------------------ compactar

    @Property(str, notify=alterado)
    def estado(self) -> str:
        return self._estado

    @Property(float, notify=alteradoProgresso)
    def progresso(self) -> float:
        return self._progresso

    @Property(str, notify=alterado)
    def mensagem(self) -> str:
        return self._mensagem

    @Property(str, notify=alterado)
    def tomMensagem(self) -> str:
        return self._tom_mensagem

    @Property(int, notify=alterado)
    def totalSaidas(self) -> int:
        return len(self._saidas)

    @Slot()
    def compactar(self) -> None:
        if self._tarefa or not self._fila.rowCount():
            return
        itens = [(i["caminho"], i["tipo"]) for i in self._fila.itens()]
        nivel, pasta = self._nivel, self._pasta or None
        for i in range(len(itens)):
            self._fila.atualizar(i, estado="na fila", tom="normal", progresso=-1.0)
        self._estado, self._mensagem, self._saidas, self._progresso = "compactando", "", [], 0.0
        tarefa = Tarefa(lambda ao_evento, cancelado: servico.processar_fila(itens, nivel, pasta, ao_evento, cancelado),
                        self)
        tarefa.progresso.connect(self._aoEvento)
        tarefa.concluida.connect(self._aoConcluir)
        tarefa.falhou.connect(self._aoFalhar)
        self._tarefa = tarefa
        tarefa.start()
        self.alterado.emit()
        self.alteradoProgresso.emit()

    @Slot(object)
    def _aoEvento(self, evento) -> None:
        if "total" in evento:
            self._progresso = evento["total"]
            self.alteradoProgresso.emit()
            return
        i, estado = evento["i"], evento["estado"]
        if estado == "compactando":
            self._fila.atualizar(i, estado="compactando…", tom="ativo", progresso=evento["fracao"])
        elif estado == "erro":
            self._fila.atualizar(i, estado=evento["mensagem"], tom="erro", progresso=-1.0)
        else:
            r: servico.Resultado = evento["resultado"]
            if r.saida is None:
                self._fila.atualizar(i, estado="Já estava compacto", tom="normal", progresso=-1.0)
                return
            texto = (f"{arquivo.tamanho_legivel(r.antes)} → {arquivo.tamanho_legivel(r.depois)} · "
                     f"{_reducao(r.antes, r.depois)}")
            self._fila.atualizar(i, estado=texto + (f" · {r.aviso}" if r.aviso else ""),
                                 tom="aviso" if r.aviso else "sucesso", progresso=-1.0)

    @Slot(object)
    def _aoConcluir(self, retorno) -> None:
        self._tarefa = None
        feitos = [r for r in retorno["resultados"] if r is not None]
        salvos = [r for r in feitos if r.saida]
        self._saidas = [str(r.saida) for r in salvos]
        erros = sum(1 for item in self._fila.itens() if item["tom"] == "erro")
        if retorno["cancelado"]:
            for i, item in enumerate(self._fila.itens()):
                if item["tom"] in ("normal", "ativo") and item["estado"] in ("na fila", "compactando…"):
                    self._fila.atualizar(i, estado="cancelado", tom="normal", progresso=-1.0)
        if salvos:
            antes, depois = sum(r.antes for r in salvos), sum(r.depois for r in salvos)
            self._mensagem = (f"{len(salvos)} arquivo{'s' if len(salvos) > 1 else ''} compactado"
                              f"{'s' if len(salvos) > 1 else ''} · economizou "
                              f"{arquivo.tamanho_legivel(antes - depois)} ({_reducao(antes, depois)})")
            self._tom_mensagem = "sucesso"
        elif feitos:
            self._mensagem = ("Nada ficou menor: já estava compacto. Tente o nível Forte."
                              if self._nivel != "forte" else "Nada ficou menor: já estava compacto.")
            self._tom_mensagem = "aviso"
        else:
            self._mensagem, self._tom_mensagem = "Nenhum arquivo foi compactado.", "erro"
        if erros:
            self._mensagem += f" · {erros} com erro (veja a fila)"
            self._tom_mensagem = "aviso" if salvos else self._tom_mensagem
        if retorno["cancelado"]:
            self._mensagem = "Parado. " + self._mensagem
            self._tom_mensagem = "aviso"
        self._estado, self._progresso = "concluido", 1.0 if not retorno["cancelado"] else self._progresso
        self.alterado.emit()
        self.alteradoProgresso.emit()

    @Slot(str)
    def _aoFalhar(self, mensagem: str) -> None:
        self._tarefa = None
        self._estado, self._mensagem, self._tom_mensagem = "concluido", mensagem, "erro"
        self.alterado.emit()

    @Slot()
    def cancelar(self) -> None:
        if self._tarefa:
            self._tarefa.cancelar()

    # ------------------------------------------------------------ resultado

    @Slot()
    def abrirArquivo(self) -> None:
        if len(self._saidas) == 1 and Path(self._saidas[0]).exists():
            os.startfile(self._saidas[0])

    @Slot()
    def abrirPasta(self) -> None:
        if self._saidas and Path(self._saidas[0]).exists():
            subprocess.Popen(["explorer", "/select,", self._saidas[0]])
