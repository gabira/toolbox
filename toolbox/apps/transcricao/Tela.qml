import QtQuick
import QtQuick.Dialogs
import "../../ui/tema"
import "../../ui/componentes"

Item {
    id: tela

    property var controlador
    property color cor: Tema.destaque

    readonly property var c: controlador
    readonly property var analise: c.analise
    readonly property bool trabalhando: c.estado === "trabalhando"
    readonly property bool podeTranscrever: analise.estado === "ok" && !trabalhando

    Component.onCompleted: c.definirArquivo(nucleo.arquivo)

    Connections {
        target: nucleo
        function onEntradaAlterada() { tela.c.definirArquivo(nucleo.arquivo) }
    }

    component Rotulo: Text {
        color: Tema.texto
        font.family: Tema.fonte
        font.pixelSize: 15
    }

    Flickable {
        id: rolagem
        anchors.fill: parent
        contentHeight: coluna.height + 40
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        Column {
            id: coluna
            width: Math.min(680, tela.width - 64)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 14

            // --- Arquivo ---
            Cartao {
                titulo: "Áudio ou vídeo"
                width: parent.width

                Item {
                    width: parent.width
                    height: 48

                    Rectangle {
                        id: fundoIcone
                        width: 48
                        height: 48
                        radius: 14
                        color: Tema.comAlfa(tela.cor, 0.18)
                        Icone {
                            anchors.centerIn: parent
                            fonte: Qt.resolvedUrl("icone.svg")
                            width: 24
                            height: 24
                        }
                    }
                    Column {
                        anchors {
                            left: fundoIcone.right; leftMargin: 14
                            right: botaoTrocar.left; rightMargin: 14
                            verticalCenter: parent.verticalCenter
                        }
                        spacing: 2
                        Rotulo {
                            width: parent.width
                            text: nucleo.nomeArquivo !== "" ? nucleo.nomeArquivo : "Nenhum arquivo selecionado"
                            elide: Text.ElideMiddle
                            font.pixelSize: 16
                            font.weight: Font.DemiBold
                        }
                        Rotulo {
                            width: parent.width
                            elide: Text.ElideRight
                            color: tela.analise.estado === "erro" ? Tema.erro : Tema.textoSuave
                            font.pixelSize: 12
                            text: {
                                if (nucleo.arquivo === "")
                                    return "Arraste um áudio ou vídeo para a janela ou escolha um arquivo."
                                if (tela.analise.estado === "analisando")
                                    return "Analisando…"
                                if (tela.analise.estado === "erro")
                                    return tela.analise.mensagem
                                return nucleo.resumoArquivo + (tela.analise.duracao ? " · " + tela.analise.duracao : "")
                            }
                        }
                    }
                    Botao {
                        id: botaoTrocar
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        texto: nucleo.arquivo !== "" ? "Trocar" : "Escolher arquivo"
                        icone: "pasta"
                        cor: tela.cor
                        habilitado: !tela.trabalhando
                        onClicado: dialogoArquivo.open()
                    }
                }

            }

            // --- Modelo ---
            Cartao {
                titulo: "Qualidade"
                width: parent.width

                Grid {
                    id: gradeModelos
                    width: parent.width
                    columns: 2
                    spacing: 10
                    Repeater {
                        model: tela.c.modelos
                        OpcaoSelecao {
                            required property var modelData
                            width: (gradeModelos.width - gradeModelos.spacing) / 2
                            titulo: modelData.nome
                            subtitulo: modelData.descricao
                            selo: modelData.selo
                            cor: tela.cor
                            selecionada: tela.c.modelo === modelData.id
                            habilitada: !tela.trabalhando
                            onClicada: tela.c.definirModelo(modelData.id)
                        }
                    }
                }
                Rotulo {
                    width: parent.width
                    wrapMode: Text.Wrap
                    color: Tema.textoSuave
                    font.pixelSize: 12
                    text: {
                        const atual = tela.c.modelos.find(m => m.id === tela.c.modelo)
                        const offline = "Tudo roda no seu computador, sem internet: o áudio não sai da máquina."
                        if (atual && !atual.baixado)
                            return offline + " Na 1ª vez os modelos (" + atual.tamanho + ") são baixados e ficam guardados."
                        return offline
                    }
                }

                Row {
                    spacing: 16
                    Rotulo {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Idioma"
                        color: Tema.textoSuave
                        font.pixelSize: 13
                    }
                    Repeater {
                        model: tela.c.idiomas
                        CaixaMarcar {
                            required property var modelData
                            texto: modelData.nome
                            marcada: tela.c.idioma === modelData.id
                            cor: tela.cor
                            habilitada: !tela.trabalhando
                            onAlternada: tela.c.definirIdioma(modelData.id)
                        }
                    }
                }
            }

            // --- Quem fala ---
            Cartao {
                titulo: "Quem fala"
                width: parent.width

                CaixaMarcar {
                    texto: "Separar as pessoas que falam (Pessoa 1, Pessoa 2…)"
                    marcada: tela.c.separar
                    cor: tela.cor
                    habilitada: !tela.trabalhando
                    onAlternada: (valor) => tela.c.definirSeparar(valor)
                }
                Rotulo {
                    width: parent.width
                    wrapMode: Text.Wrap
                    color: Tema.textoSuave
                    font.pixelSize: 12
                    text: tela.c.separar
                          ? "Reconhece cada voz diferente, em qualquer áudio. A primeira a falar é a Pessoa 1. Se só uma pessoa falar, o texto sai corrido."
                          : "O texto sai corrido, em parágrafos, sem indicar quem falou."
                }
            }

            // --- Saída ---
            Cartao {
                titulo: "Salvar como"
                width: parent.width

                Row {
                    spacing: 22
                    Repeater {
                        model: tela.c.formatos
                        CaixaMarcar {
                            required property var modelData
                            texto: modelData.nome
                            marcada: modelData.marcado
                            cor: tela.cor
                            habilitada: !tela.trabalhando
                            onAlternada: (valor) => tela.c.marcarFormato(modelData.id, valor)
                        }
                    }
                }

                Rotulo {
                    text: "Nome dos arquivos"
                    color: Tema.textoSuave
                    font.pixelSize: 13
                    topPadding: 4
                }
                CampoTexto {
                    width: parent.width
                    texto: tela.c.nomeSaida
                    dica: tela.c.nomePadrao !== "" ? tela.c.nomePadrao : "Nome do arquivo"
                    cor: tela.cor
                    habilitado: !tela.trabalhando && nucleo.arquivo !== ""
                    onEditado: (texto) => tela.c.definirNome(texto)
                    onConfirmado: if (tela.podeTranscrever) tela.c.transcrever()
                }

                Rotulo {
                    text: "Salvar em"
                    color: Tema.textoSuave
                    font.pixelSize: 13
                    topPadding: 4
                }
                Item {
                    width: parent.width
                    height: 44
                    Rotulo {
                        anchors {
                            left: parent.left
                            right: botaoPasta.left; rightMargin: 14
                            verticalCenter: parent.verticalCenter
                        }
                        text: tela.c.pastaDestino !== "" ? tela.c.pastaDestino : "A mesma pasta do arquivo"
                        color: tela.c.pastaDestino !== "" ? Tema.texto : Tema.textoSuave
                        elide: Text.ElideMiddle
                    }
                    Botao {
                        id: botaoPasta
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        texto: "Alterar"
                        icone: "pasta"
                        cor: tela.cor
                        habilitado: !tela.trabalhando && nucleo.arquivo !== ""
                        onClicado: dialogoPasta.open()
                    }
                }
                Rotulo {
                    visible: tela.c.previsaoSaida !== ""
                    width: parent.width
                    elide: Text.ElideMiddle
                    color: Tema.textoSuave
                    font.pixelSize: 12
                    textFormat: Text.StyledText
                    text: "Será salvo como <b><font color='" + Tema.texto + "'>"
                          + tela.c.previsaoSaida.replace(/&/g, "&amp;").replace(/</g, "&lt;")
                          + "</font></b>"
                }
            }

            // --- Ação ---
            Item {
                width: parent.width
                height: 56

                Botao {
                    anchors.fill: parent
                    primario: true
                    cor: tela.cor
                    texto: {
                        const atual = tela.c.modelos.find(m => m.id === tela.c.modelo)
                        return atual && !atual.baixado ? "Baixar o modelo e transcrever" : "Transcrever"
                    }
                    habilitado: tela.podeTranscrever
                    opacity: tela.trabalhando ? 0 : (habilitado ? 1 : 0.4)
                    visible: opacity > 0
                    onClicado: tela.c.transcrever()
                }

                Item {
                    anchors.fill: parent
                    opacity: tela.trabalhando ? 1 : 0
                    visible: opacity > 0
                    Behavior on opacity { NumberAnimation { duration: Tema.rapida } }

                    Rotulo {
                        id: porcentagem
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        width: 52
                        text: Math.round(tela.c.progresso * 100) + "%"
                        font.weight: Font.Bold
                    }
                    BarraProgresso {
                        anchors {
                            left: porcentagem.right
                            right: botaoCancelar.left; rightMargin: 16
                            verticalCenter: parent.verticalCenter
                        }
                        valor: tela.c.progresso
                        cor: tela.cor
                    }
                    Botao {
                        id: botaoCancelar
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        texto: "Cancelar"
                        cor: Tema.erro
                        onClicado: tela.c.cancelar()
                    }
                }
            }
            Rotulo {
                visible: tela.trabalhando
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                color: Tema.textoSuave
                font.pixelSize: 13
                text: tela.c.textoProgresso
            }

            // --- Resultado ---
            Rectangle {
                readonly property bool sucesso: tela.c.estado === "concluido"
                readonly property color corResultado: sucesso ? Tema.sucesso : Tema.erro

                width: parent.width
                height: Math.max(64, textoResultado.implicitHeight + 28)
                radius: 16
                visible: sucesso || tela.c.estado === "erro"
                color: Tema.comAlfa(corResultado, 0.1)
                border.width: 1
                border.color: Tema.comAlfa(corResultado, 0.5)

                Icone {
                    id: iconeResultado
                    anchors.left: parent.left
                    anchors.leftMargin: 18
                    anchors.verticalCenter: parent.verticalCenter
                    nome: parent.sucesso ? "check" : "alerta"
                    width: 22
                    height: 22
                }
                Rotulo {
                    id: textoResultado
                    anchors {
                        left: iconeResultado.right; leftMargin: 12
                        right: botoesResultado.visible ? botoesResultado.left : parent.right; rightMargin: 14
                        verticalCenter: parent.verticalCenter
                    }
                    text: tela.c.mensagem
                    wrapMode: Text.Wrap
                    maximumLineCount: 3
                    elide: Text.ElideRight
                }
                Row {
                    id: botoesResultado
                    visible: parent.sucesso
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    Botao {
                        visible: tela.c.temDocumento
                        texto: "Abrir no Word"
                        cor: Tema.sucesso
                        onClicado: tela.c.abrirDocumento()
                    }
                    Botao {
                        texto: "Abrir pasta"
                        icone: "pasta"
                        cor: Tema.sucesso
                        onClicado: tela.c.abrirPasta()
                    }
                }
            }

            // --- Texto ao vivo ---
            Cartao {
                titulo: tela.trabalhando ? "Texto até agora" : "Texto"
                width: parent.width
                visible: tela.c.texto !== ""

                Flickable {
                    id: rolagemTexto
                    width: parent.width
                    height: Math.min(260, textoAoVivo.implicitHeight)
                    contentHeight: textoAoVivo.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    // Acompanha o fim do texto enquanto a transcrição anda.
                    onContentHeightChanged: if (tela.trabalhando) contentY = Math.max(0, contentHeight - height)

                    TextEdit {
                        id: textoAoVivo
                        width: rolagemTexto.width
                        text: tela.c.texto
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextEdit.Wrap
                        color: Tema.texto
                        selectionColor: Tema.comAlfa(tela.cor, 0.5)
                        font.family: Tema.fonte
                        font.pixelSize: 14
                    }
                }
            }
        }
    }

    FileDialog {
        id: dialogoArquivo
        title: "Escolha um áudio ou vídeo"
        nameFilters: [
            "Áudio e vídeo (*.mp3 *.m4a *.wav *.flac *.ogg *.opus *.aac *.wma *.mp4 *.mkv *.mov *.avi *.webm *.wmv)",
            "Todos os arquivos (*)"
        ]
        onAccepted: nucleo.definirArquivo(selectedFile.toString())
    }

    FolderDialog {
        id: dialogoPasta
        title: "Onde salvar a transcrição"
        currentFolder: tela.c.pastaDestinoUrl
        onAccepted: tela.c.definirPasta(selectedFolder.toString())
    }
}
