import QtQuick
import QtQuick.Dialogs
import "../../ui/tema"
import "../../ui/componentes"

Item {
    id: tela

    property var controlador
    property color cor: Tema.destaque

    readonly property var analise: controlador.analise
    readonly property bool extraindo: controlador.estado === "extraindo"
    readonly property bool podeExtrair: analise.estado === "ok" && !extraindo

    Component.onCompleted: controlador.analisar(nucleo.arquivo)

    Connections {
        target: nucleo
        function onArquivoAlterado() { tela.controlador.analisar(nucleo.arquivo) }
    }

    component Rotulo: Text {
        color: Tema.texto
        font.family: Tema.fonte
        font.pixelSize: 15
    }

    component Chip: Rectangle {
        property alias texto: rotuloChip.text
        property bool forte: false
        width: rotuloChip.implicitWidth + 20
        height: 28
        radius: 14
        color: forte ? Tema.comAlfa(tela.cor, 0.22) : Tema.comAlfa(Tema.texto, 0.06)
        border.width: 1
        border.color: forte ? Tema.comAlfa(tela.cor, 0.7) : Tema.borda
        Text {
            id: rotuloChip
            anchors.centerIn: parent
            color: Tema.texto
            font.family: Tema.fonte
            font.pixelSize: 13
            font.weight: parent.forte ? Font.Bold : Font.Normal
        }
    }

    Flickable {
        anchors.fill: parent
        contentHeight: coluna.height + 40
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        Column {
            id: coluna
            width: Math.min(680, tela.width - 64)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 14

            // --- Vídeo ---
            Cartao {
                titulo: "Vídeo"
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
                            nome: "video"
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
                            text: nucleo.nomeArquivo !== "" ? nucleo.nomeArquivo : "Nenhum vídeo selecionado"
                            elide: Text.ElideMiddle
                            font.pixelSize: 16
                            font.weight: Font.DemiBold
                        }
                        Rotulo {
                            width: parent.width
                            elide: Text.ElideRight
                            color: Tema.textoSuave
                            font.pixelSize: 12
                            text: {
                                if (nucleo.arquivo === "")
                                    return "Arraste um vídeo para a janela ou escolha um arquivo."
                                if (tela.analise.estado === "ok" && tela.analise.duracao)
                                    return nucleo.resumoArquivo + " · " + tela.analise.duracao
                                return nucleo.resumoArquivo
                            }
                        }
                    }

                    Botao {
                        id: botaoTrocar
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        texto: nucleo.arquivo !== "" ? "Trocar" : "Escolher vídeo"
                        icone: "pasta"
                        cor: tela.cor
                        habilitado: !tela.extraindo
                        onClicado: dialogoVideo.open()
                    }
                }
            }

            // --- Áudio detectado ---
            Cartao {
                titulo: "Áudio detectado"
                width: parent.width

                Rotulo {
                    visible: tela.analise.estado === "vazio" || tela.analise.estado === "analisando"
                    color: Tema.textoSuave
                    text: tela.analise.estado === "analisando" ? "Analisando o vídeo…" : "Escolha um vídeo para ver a faixa de áudio."
                }

                Row {
                    visible: tela.analise.estado === "erro"
                    spacing: 10
                    Icone { nome: "alerta"; width: 20; height: 20; anchors.verticalCenter: parent.verticalCenter }
                    Rotulo { text: tela.analise.mensagem || ""; color: Tema.erro }
                }

                Flow {
                    visible: tela.analise.estado === "ok"
                    width: parent.width
                    spacing: 8
                    Chip { texto: tela.analise.codec || ""; forte: true }
                    Repeater {
                        model: tela.analise.detalhes || []
                        Chip { required property string modelData; texto: modelData }
                    }
                }

                Rotulo {
                    visible: tela.analise.estado === "ok" && tela.analise.faixas > 1
                    color: Tema.textoSuave
                    font.pixelSize: 12
                    text: "O vídeo tem " + tela.analise.faixas + " faixas de áudio; será extraída a primeira."
                }
            }

            // --- Formato ---
            Cartao {
                titulo: "Formato de saída"
                width: parent.width

                Grid {
                    id: grade
                    width: parent.width
                    columns: 2
                    spacing: 10

                    Repeater {
                        model: tela.controlador.formatos
                        OpcaoSelecao {
                            required property var modelData
                            width: (grade.width - grade.spacing) / 2
                            titulo: modelData.nome
                            subtitulo: modelData.id === "original" && tela.analise.extensao
                                       ? modelData.descricao + " (." + tela.analise.extensao + ")"
                                       : modelData.descricao
                            selo: modelData.selo
                            cor: tela.cor
                            selecionada: tela.controlador.formato === modelData.id
                            habilitada: !tela.extraindo
                            onClicada: tela.controlador.definirFormato(modelData.id)
                        }
                    }
                }
            }

            // --- Saída: nome (opcional) e pasta ---
            Cartao {
                titulo: "Saída"
                width: parent.width

                Rotulo {
                    text: "Nome do arquivo (opcional)"
                    color: Tema.textoSuave
                    font.pixelSize: 13
                }

                Item {
                    width: parent.width
                    height: 44

                    CampoTexto {
                        anchors {
                            left: parent.left
                            right: botaoRestaurar.visible ? botaoRestaurar.left : parent.right
                            rightMargin: botaoRestaurar.visible ? 10 : 0
                            verticalCenter: parent.verticalCenter
                        }
                        texto: tela.controlador.nomeSaida
                        dica: tela.controlador.nomePadrao !== "" ? tela.controlador.nomePadrao : "Nome do vídeo"
                        sufixo: tela.controlador.extensaoSaida !== "" ? "." + tela.controlador.extensaoSaida : ""
                        cor: tela.cor
                        habilitado: !tela.extraindo && nucleo.arquivo !== ""
                        onEditado: (texto) => tela.controlador.definirNome(texto)
                        onConfirmado: if (tela.podeExtrair) tela.controlador.extrair(nucleo.arquivo)
                    }

                    Botao {
                        id: botaoRestaurar
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        visible: tela.controlador.nomeSaida !== tela.controlador.nomePadrao && tela.controlador.nomePadrao !== ""
                        texto: "Nome original"
                        cor: tela.cor
                        habilitado: !tela.extraindo
                        onClicado: tela.controlador.definirNome(tela.controlador.nomePadrao)
                    }
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
                        text: tela.controlador.pastaDestino
                        elide: Text.ElideMiddle
                    }
                    Botao {
                        id: botaoPasta
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        texto: "Alterar"
                        icone: "pasta"
                        cor: tela.cor
                        habilitado: !tela.extraindo
                        onClicado: dialogoPasta.open()
                    }
                }

                Rotulo {
                    visible: tela.controlador.previsaoSaida !== ""
                    width: parent.width
                    elide: Text.ElideMiddle
                    color: Tema.textoSuave
                    font.pixelSize: 12
                    textFormat: Text.StyledText
                    text: "Será salvo como <b><font color='" + Tema.texto + "'>"
                          + tela.controlador.previsaoSaida.replace(/&/g, "&amp;").replace(/</g, "&lt;")
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
                    texto: "Extrair áudio"
                    habilitado: tela.podeExtrair
                    opacity: tela.extraindo ? 0 : (habilitado ? 1 : 0.4)
                    visible: opacity > 0
                    onClicado: tela.controlador.extrair(nucleo.arquivo)
                }

                Item {
                    anchors.fill: parent
                    opacity: tela.extraindo ? 1 : 0
                    visible: opacity > 0
                    Behavior on opacity { NumberAnimation { duration: Tema.rapida } }

                    Rotulo {
                        id: porcentagem
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        width: 52
                        text: Math.round(tela.controlador.progresso * 100) + "%"
                        font.weight: Font.Bold
                    }
                    BarraProgresso {
                        anchors {
                            left: porcentagem.right
                            right: botaoCancelar.left; rightMargin: 16
                            verticalCenter: parent.verticalCenter
                        }
                        valor: tela.controlador.progresso
                        cor: tela.cor
                    }
                    Botao {
                        id: botaoCancelar
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        texto: "Cancelar"
                        cor: Tema.erro
                        onClicado: tela.controlador.cancelar()
                    }
                }
            }

            // --- Resultado ---
            Rectangle {
                readonly property bool sucesso: tela.controlador.estado === "concluido"
                readonly property color corResultado: sucesso ? Tema.sucesso : Tema.erro

                width: parent.width
                height: 64
                radius: 16
                visible: sucesso || tela.controlador.estado === "erro"
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
                    anchors {
                        left: iconeResultado.right; leftMargin: 12
                        right: botaoAbrir.visible ? botaoAbrir.left : parent.right; rightMargin: 14
                        verticalCenter: parent.verticalCenter
                    }
                    text: tela.controlador.mensagem
                    elide: Text.ElideMiddle
                    maximumLineCount: 2
                    wrapMode: Text.Wrap
                }
                Botao {
                    id: botaoAbrir
                    visible: parent.sucesso
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    texto: "Abrir pasta"
                    icone: "pasta"
                    cor: Tema.sucesso
                    onClicado: tela.controlador.abrirPasta()
                }
            }
        }
    }

    FileDialog {
        id: dialogoVideo
        title: "Escolha um vídeo"
        nameFilters: [
            "Vídeos (*.mp4 *.mkv *.mov *.avi *.webm *.wmv *.flv *.m4v *.ts *.mts *.m2ts *.3gp *.mpg *.mpeg *.ogv)",
            "Todos os arquivos (*)"
        ]
        onAccepted: nucleo.definirArquivo(selectedFile.toString())
    }

    FolderDialog {
        id: dialogoPasta
        title: "Onde salvar o áudio"
        currentFolder: tela.controlador.pastaDestinoUrl
        onAccepted: tela.controlador.definirPasta(selectedFolder.toString())
    }
}
