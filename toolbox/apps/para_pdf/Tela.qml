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
    readonly property bool convertendo: c.estado === "convertendo"
    readonly property bool eImagem: analise.categoria === "imagem"
    readonly property bool podeConverter: analise.estado === "ok" && !convertendo

    Component.onCompleted: c.analisar(nucleo.arquivo)
    Connections {
        target: nucleo
        function onEntradaAlterada() { tela.c.analisar(nucleo.arquivo) }
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

    // Botãozinho só de ícone (subir, descer, remover)
    component BotaoIcone: Rectangle {
        id: botaoIcone
        property string icone: ""
        property real giro: 0
        property bool habilitado: true
        signal clicado()
        width: 32
        height: 32
        radius: 10
        opacity: habilitado ? 1 : 0.3
        color: areaIcone.containsMouse && habilitado ? Tema.comAlfa(tela.cor, 0.22) : "transparent"
        border.width: 1
        border.color: Tema.borda
        Icone {
            anchors.centerIn: parent
            nome: botaoIcone.icone
            width: 14
            height: 14
            resolucao: 28
            rotation: botaoIcone.giro
        }
        MouseArea {
            id: areaIcone
            anchors.fill: parent
            hoverEnabled: true
            enabled: botaoIcone.habilitado
            cursorShape: Qt.PointingHandCursor
            onClicked: botaoIcone.clicado()
        }
    }

    component BarraIndeterminada: Rectangle {
        id: barraInd
        height: 8
        radius: 4
        clip: true
        color: Tema.comAlfa(tela.cor, 0.15)
        Rectangle {
            width: barraInd.width * 0.3
            height: parent.height
            radius: 4
            color: tela.cor
            NumberAnimation on x {
                from: -barraInd.width * 0.3
                to: barraInd.width
                duration: 1100
                loops: Animation.Infinite
                running: barraInd.visible
            }
        }
    }

    Flickable {
        anchors.fill: parent
        contentHeight: coluna.height + 40
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        Column {
            id: coluna
            width: Math.min(700, tela.width - 64)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 14

            // --- Arquivo ---
            Cartao {
                titulo: "Arquivo"
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
                        Icone { anchors.centerIn: parent; fonte: Qt.resolvedUrl("icone.svg"); width: 26; height: 26 }
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
                            color: Tema.textoSuave
                            font.pixelSize: 12
                            text: nucleo.arquivo !== "" ? nucleo.resumoArquivo
                                                        : "Arraste uma imagem, documento, planilha ou texto para a janela."
                        }
                    }
                    Botao {
                        id: botaoTrocar
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        texto: nucleo.arquivo !== "" ? "Trocar" : "Escolher arquivo"
                        icone: "pasta"
                        cor: tela.cor
                        habilitado: !tela.convertendo
                        onClicado: dialogoArquivo.open()
                    }
                }
            }

            // --- Conversão ---
            Cartao {
                titulo: "Conversão"
                width: parent.width
                visible: tela.analise.estado !== "vazio"

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
                    Chip { texto: (tela.analise.nomeCategoria || "") + "  →  PDF"; forte: true }
                    Chip { texto: tela.analise.motor || "" }
                    Chip { visible: tela.eImagem && tela.c.imagens.length > 1; texto: tela.c.imagens.length + " páginas" }
                }
                Rotulo {
                    visible: tela.analise.estado === "ok" && tela.analise.demorado === true
                    width: parent.width
                    wrapMode: Text.Wrap
                    color: Tema.textoApagado
                    font.pixelSize: 12
                    text: "O programa é aberto escondido em segundo plano; a conversão leva alguns segundos."
                }
            }

            // --- Páginas (só imagens) ---
            Cartao {
                titulo: "Páginas do PDF"
                width: parent.width
                visible: tela.eImagem

                Repeater {
                    id: repetidorImagens
                    model: tela.c.imagens

                    delegate: Item {
                        id: linhaImagem
                        required property var modelData
                        required property int index
                        width: parent ? parent.width : 0
                        height: 52

                        Rectangle {
                            id: miniatura
                            width: 44
                            height: 44
                            radius: 8
                            anchors.verticalCenter: parent.verticalCenter
                            color: Tema.comAlfa(Tema.texto, 0.06)
                            clip: true
                            Image {
                                anchors.fill: parent
                                anchors.margins: 2
                                source: linhaImagem.modelData.url
                                sourceSize: Qt.size(88, 88)
                                fillMode: Image.PreserveAspectCrop
                                asynchronous: true
                            }
                        }
                        Column {
                            anchors {
                                left: miniatura.right; leftMargin: 12
                                right: botoesImagem.left; rightMargin: 12
                                verticalCenter: parent.verticalCenter
                            }
                            Rotulo {
                                width: parent.width
                                elide: Text.ElideMiddle
                                font.pixelSize: 14
                                text: (linhaImagem.index + 1) + ". " + linhaImagem.modelData.nome
                            }
                            Rotulo {
                                color: Tema.textoApagado
                                font.pixelSize: 12
                                text: linhaImagem.modelData.detalhe
                            }
                        }
                        Row {
                            id: botoesImagem
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 6
                            visible: repetidorImagens.count > 1
                            BotaoIcone {
                                icone: "seta"; giro: -90
                                habilitado: linhaImagem.index > 0 && !tela.convertendo
                                onClicado: tela.c.moverImagem(linhaImagem.index, -1)
                            }
                            BotaoIcone {
                                icone: "seta"; giro: 90
                                habilitado: linhaImagem.index < repetidorImagens.count - 1 && !tela.convertendo
                                onClicado: tela.c.moverImagem(linhaImagem.index, 1)
                            }
                            BotaoIcone {
                                icone: "fechar"
                                habilitado: !tela.convertendo
                                onClicado: tela.c.removerImagem(linhaImagem.index)
                            }
                        }
                    }
                }

                Botao {
                    texto: "Adicionar imagens"
                    icone: "pasta"
                    cor: tela.cor
                    habilitado: !tela.convertendo
                    onClicado: dialogoImagens.open()
                }

                Rotulo {
                    text: "Tamanho da página"
                    color: Tema.textoSuave
                    font.pixelSize: 13
                    topPadding: 6
                }
                Grid {
                    id: gradePagina
                    width: parent.width
                    columns: 2
                    spacing: 10
                    OpcaoSelecao {
                        width: (gradePagina.width - gradePagina.spacing) / 2
                        titulo: "Tamanho da imagem"
                        subtitulo: "Página do tamanho exato, sem margens"
                        selo: "Recomendado"
                        cor: tela.cor
                        selecionada: tela.c.pagina === "imagem"
                        habilitada: !tela.convertendo
                        onClicada: tela.c.definirPagina("imagem")
                    }
                    OpcaoSelecao {
                        width: (gradePagina.width - gradePagina.spacing) / 2
                        titulo: "Folha A4"
                        subtitulo: "Com margem; gira para imagens deitadas"
                        cor: tela.cor
                        selecionada: tela.c.pagina === "a4"
                        habilitada: !tela.convertendo
                        onClicada: tela.c.definirPagina("a4")
                    }
                }
            }

            // --- Saída ---
            Cartao {
                titulo: "Saída"
                width: parent.width
                visible: tela.analise.estado === "ok"

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
                        texto: tela.c.nomeSaida
                        dica: tela.c.nomePadrao
                        sufixo: ".pdf"
                        cor: tela.cor
                        habilitado: !tela.convertendo
                        onEditado: (texto) => tela.c.definirNome(texto)
                        onConfirmado: if (tela.podeConverter) tela.c.converter()
                    }
                    Botao {
                        id: botaoRestaurar
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        visible: tela.c.nomeSaida !== tela.c.nomePadrao && tela.c.nomePadrao !== ""
                        texto: "Nome original"
                        cor: tela.cor
                        habilitado: !tela.convertendo
                        onClicado: tela.c.definirNome(tela.c.nomePadrao)
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
                        text: tela.c.pastaDestino
                        elide: Text.ElideMiddle
                    }
                    Botao {
                        id: botaoPasta
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        texto: "Alterar"
                        icone: "pasta"
                        cor: tela.cor
                        habilitado: !tela.convertendo
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
                          + tela.c.previsaoSaida.replace(/&/g, "&amp;").replace(/</g, "&lt;") + "</font></b>"
                }
            }

            // --- Ação ---
            Item {
                width: parent.width
                height: 56
                visible: tela.analise.estado === "ok"

                Botao {
                    anchors.fill: parent
                    primario: true
                    cor: tela.cor
                    texto: "Converter para PDF"
                    iconeFonte: Qt.resolvedUrl("icone.svg")
                    habilitado: tela.podeConverter
                    visible: !tela.convertendo
                    onClicado: tela.c.converter()
                }

                Item {
                    anchors.fill: parent
                    visible: tela.convertendo

                    Rotulo {
                        id: porcentagem
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        width: tela.analise.demorado ? 0 : 52
                        visible: !tela.analise.demorado
                        text: Math.round(tela.c.progresso * 100) + "%"
                        font.weight: Font.Bold
                    }
                    BarraProgresso {
                        visible: !tela.analise.demorado
                        anchors {
                            left: porcentagem.right
                            right: botaoCancelar.left; rightMargin: 16
                            verticalCenter: parent.verticalCenter
                        }
                        valor: tela.c.progresso
                        cor: tela.cor
                    }
                    Column {
                        visible: tela.analise.demorado === true
                        anchors {
                            left: parent.left
                            right: botaoCancelar.left; rightMargin: 16
                            verticalCenter: parent.verticalCenter
                        }
                        spacing: 8
                        Rotulo {
                            text: "Convertendo " + (tela.analise.motor || "").replace("Via ", "com o ") + "…"
                            color: Tema.textoSuave
                            font.pixelSize: 13
                        }
                        BarraIndeterminada { width: parent.width }
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

            // --- Resultado ---
            Rectangle {
                readonly property bool sucesso: tela.c.estado === "concluido"
                readonly property color corResultado: sucesso ? Tema.sucesso : Tema.erro

                width: parent.width
                height: 64
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
                    anchors {
                        left: iconeResultado.right; leftMargin: 12
                        right: botoesResultado.visible ? botoesResultado.left : parent.right; rightMargin: 12
                        verticalCenter: parent.verticalCenter
                    }
                    text: tela.c.mensagem
                    wrapMode: Text.Wrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }
                Row {
                    id: botoesResultado
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    visible: parent.sucesso
                    Botao {
                        texto: "Abrir PDF"
                        cor: Tema.sucesso
                        onClicado: tela.c.abrirPdf()
                    }
                    Botao {
                        texto: "Abrir pasta"
                        icone: "pasta"
                        cor: Tema.sucesso
                        onClicado: tela.c.abrirPasta()
                    }
                }
            }
        }
    }

    FileDialog {
        id: dialogoArquivo
        title: "Escolha o arquivo para converter em PDF"
        nameFilters: [
            "Arquivos compatíveis (*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp *.docx *.doc *.rtf *.odt *.xlsx *.xls *.ods *.csv *.pptx *.ppt *.odp *.txt *.md *.html *.htm)",
            "Todos os arquivos (*)"
        ]
        onAccepted: nucleo.definirArquivo(selectedFile.toString())
    }

    FileDialog {
        id: dialogoImagens
        title: "Adicionar imagens ao PDF"
        fileMode: FileDialog.OpenFiles
        nameFilters: ["Imagens (*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp)"]
        onAccepted: {
            const urls = []
            for (let i = 0; i < selectedFiles.length; i++)
                urls.push(selectedFiles[i].toString())
            tela.c.adicionarImagens(urls)
        }
    }

    FolderDialog {
        id: dialogoPasta
        title: "Onde salvar o PDF"
        currentFolder: tela.c.pastaDestinoUrl
        onAccepted: tela.c.definirPasta(selectedFolder.toString())
    }
}
