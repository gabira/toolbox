import QtQuick
import QtQuick.Dialogs
import "../../ui/tema"
import "../../ui/componentes"

Item {
    id: tela

    property var controlador
    property color cor: Tema.destaque

    readonly property var c: controlador
    readonly property bool compactando: c.estado === "compactando"
    readonly property color amarelo: "#FBBF24"

    function corTom(tom) {
        switch (tom) {
        case "sucesso": return Tema.sucesso
        case "erro": return Tema.erro
        case "aviso": return tela.amarelo
        case "ativo": return Qt.lighter(tela.cor, 1.35)
        default: return Tema.textoSuave
        }
    }

    Component.onCompleted: c.receberArquivo(nucleo.arquivo)
    Connections {
        target: nucleo
        function onEntradaAlterada() { tela.c.receberArquivo(nucleo.arquivo) }
    }

    component Rotulo: Text {
        color: Tema.texto
        font.family: Tema.fonte
        font.pixelSize: 15
    }

    component BarraIndeterminada: Rectangle {
        id: barraInd
        height: 4
        radius: 2
        clip: true
        color: Tema.comAlfa(tela.cor, 0.15)
        Rectangle {
            width: barraInd.width * 0.3
            height: parent.height
            radius: 2
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

            // --- Arquivos ---
            Cartao {
                titulo: "Arquivos"
                width: parent.width

                Rotulo {
                    visible: repetidorFila.count === 0
                    width: parent.width
                    wrapMode: Text.Wrap
                    color: Tema.textoSuave
                    font.pixelSize: 13
                    text: "Arraste um PDF ou uma imagem (JPG, PNG, WebP) para a janela, ou adicione vários de uma vez."
                }

                Repeater {
                    id: repetidorFila
                    model: tela.c.fila

                    delegate: Item {
                        id: itemFila
                        required property int index
                        required property string nome
                        required property string detalhe
                        required property string estado
                        required property string tom
                        required property real progresso
                        required property string miniatura

                        width: parent ? parent.width : 0
                        height: 56

                        Rectangle {
                            id: fundoMiniatura
                            width: 44
                            height: 44
                            radius: 8
                            anchors.verticalCenter: parent.verticalCenter
                            color: Tema.comAlfa(tela.cor, 0.14)
                            clip: true
                            Image {
                                id: imagemMiniatura
                                visible: itemFila.miniatura !== "" && status !== Image.Error
                                anchors.fill: parent
                                anchors.margins: 2
                                source: itemFila.miniatura
                                sourceSize: Qt.size(88, 88)
                                fillMode: Image.PreserveAspectCrop
                                asynchronous: true
                            }
                            Text {
                                visible: !imagemMiniatura.visible
                                anchors.centerIn: parent
                                text: itemFila.miniatura === "" ? "PDF" : itemFila.nome.split(".").pop().toUpperCase()
                                color: tela.cor
                                font.family: Tema.fonte
                                font.pixelSize: 12
                                font.weight: Font.Bold
                            }
                        }
                        Column {
                            anchors {
                                left: fundoMiniatura.right; leftMargin: 12
                                right: ladoDireito.left; rightMargin: 12
                                verticalCenter: parent.verticalCenter
                            }
                            spacing: 3
                            Rotulo {
                                width: parent.width
                                elide: Text.ElideMiddle
                                font.pixelSize: 14
                                text: itemFila.nome
                            }
                            Rotulo {
                                width: parent.width
                                elide: Text.ElideRight
                                font.pixelSize: 12
                                color: itemFila.estado !== "" && itemFila.tom !== "ativo" ? tela.corTom(itemFila.tom)
                                                                                         : Tema.textoApagado
                                text: itemFila.estado !== "" && itemFila.tom !== "ativo" && itemFila.estado !== "na fila"
                                      ? itemFila.estado : itemFila.detalhe
                            }
                        }
                        Item {
                            id: ladoDireito
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            width: tela.compactando ? 90 : 32
                            height: 32

                            BarraIndeterminada {
                                anchors.verticalCenter: parent.verticalCenter
                                width: parent.width
                                visible: itemFila.tom === "ativo"
                            }
                            Rotulo {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                visible: tela.compactando && itemFila.tom !== "ativo"
                                font.pixelSize: 12
                                color: tela.corTom(itemFila.tom)
                                text: itemFila.estado === "na fila" ? "na fila"
                                      : (itemFila.tom === "sucesso" || itemFila.tom === "aviso" ? "pronto" : "")
                            }
                            Rectangle {
                                anchors.fill: parent
                                visible: !tela.compactando
                                radius: 10
                                color: areaRemover.containsMouse ? Tema.comAlfa(Tema.erro, 0.18) : "transparent"
                                border.width: 1
                                border.color: Tema.borda
                                Icone { anchors.centerIn: parent; nome: "fechar"; width: 12; height: 12; resolucao: 24 }
                                MouseArea {
                                    id: areaRemover
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: tela.c.remover(itemFila.index)
                                }
                            }
                        }
                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 1
                            color: Tema.borda
                            visible: itemFila.index < repetidorFila.count - 1
                        }
                    }
                }

                Item {
                    width: parent.width
                    height: 44
                    Botao {
                        id: botaoAdicionar
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        texto: repetidorFila.count ? "Adicionar mais" : "Adicionar arquivos"
                        icone: "pasta"
                        cor: tela.cor
                        habilitado: !tela.compactando
                        onClicado: dialogoArquivos.open()
                    }
                    Rotulo {
                        anchors {
                            left: botaoAdicionar.right; leftMargin: 14
                            right: botaoLimpar.visible ? botaoLimpar.left : parent.right; rightMargin: 14
                            verticalCenter: parent.verticalCenter
                        }
                        elide: Text.ElideRight
                        color: Tema.textoSuave
                        font.pixelSize: 13
                        text: tela.c.resumoFila
                    }
                    Botao {
                        id: botaoLimpar
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        visible: repetidorFila.count > 1
                        texto: "Limpar"
                        cor: Tema.textoSuave
                        habilitado: !tela.compactando
                        onClicado: tela.c.limpar()
                    }
                }
            }

            // --- Nível ---
            Cartao {
                titulo: "Quanto compactar"
                width: parent.width

                Grid {
                    id: gradeNivel
                    width: parent.width
                    columns: 3
                    spacing: 10
                    Repeater {
                        model: tela.c.niveis
                        OpcaoSelecao {
                            required property var modelData
                            width: (gradeNivel.width - 2 * gradeNivel.spacing) / 3
                            implicitHeight: 84
                            titulo: modelData.nome
                            subtitulo: modelData.descricao
                            selo: modelData.id === "equilibrado" ? "Recomendado" : ""
                            cor: tela.cor
                            selecionada: tela.c.nivel === modelData.id
                            habilitada: !tela.compactando
                            onClicada: tela.c.definirNivel(modelData.id)
                        }
                    }
                }
                Rotulo {
                    width: parent.width
                    wrapMode: Text.Wrap
                    color: Tema.textoSuave
                    font.pixelSize: 12
                    text: "PDF: só as imagens de dentro perdem resolução; o texto continua nítido e pesquisável. "
                          + "Imagens continuam no mesmo formato, sem os dados ocultos da foto (local, câmera)."
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
                    texto: repetidorFila.count > 1 ? "Compactar " + repetidorFila.count + " arquivos" : "Compactar"
                    iconeFonte: Qt.resolvedUrl("icone.svg")
                    habilitado: repetidorFila.count > 0
                    visible: !tela.compactando
                    onClicado: tela.c.compactar()
                }

                Item {
                    anchors.fill: parent
                    visible: tela.compactando

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
                        texto: "Parar"
                        cor: Tema.erro
                        onClicado: tela.c.cancelar()
                    }
                }
            }

            // --- Resultado ---
            Rectangle {
                readonly property color corResultado: tela.corTom(tela.c.tomMensagem)

                width: parent.width
                height: Math.max(64, textoResultado.implicitHeight + 28)
                radius: 16
                visible: tela.c.mensagem !== "" && !tela.compactando
                color: Tema.comAlfa(corResultado, 0.1)
                border.width: 1
                border.color: Tema.comAlfa(corResultado, 0.5)

                Icone {
                    id: iconeResultado
                    anchors.left: parent.left
                    anchors.leftMargin: 18
                    anchors.verticalCenter: parent.verticalCenter
                    nome: tela.c.tomMensagem === "sucesso" ? "check" : "alerta"
                    width: 22
                    height: 22
                }
                Rotulo {
                    id: textoResultado
                    anchors {
                        left: iconeResultado.right; leftMargin: 12
                        right: botoesResultado.visible ? botoesResultado.left : parent.right; rightMargin: 12
                        verticalCenter: parent.verticalCenter
                    }
                    text: tela.c.mensagem
                    wrapMode: Text.Wrap
                }
                Row {
                    id: botoesResultado
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    visible: tela.c.totalSaidas > 0
                    Botao {
                        visible: tela.c.totalSaidas === 1
                        texto: "Abrir"
                        cor: Tema.sucesso
                        onClicado: tela.c.abrirArquivo()
                    }
                    Botao {
                        texto: "Abrir pasta"
                        icone: "pasta"
                        cor: Tema.sucesso
                        onClicado: tela.c.abrirPasta()
                    }
                }
            }

            // --- Saída ---
            Cartao {
                titulo: "Salvar em"
                width: parent.width

                Item {
                    width: parent.width
                    height: 44
                    Rotulo {
                        anchors {
                            left: parent.left
                            right: botoesPasta.left; rightMargin: 14
                            verticalCenter: parent.verticalCenter
                        }
                        text: tela.c.pastaDestino !== "" ? tela.c.pastaDestino : "Na mesma pasta de cada arquivo"
                        elide: Text.ElideMiddle
                    }
                    Row {
                        id: botoesPasta
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8
                        Botao {
                            visible: tela.c.pastaDestino !== ""
                            texto: "Mesma pasta"
                            cor: tela.cor
                            habilitado: !tela.compactando
                            onClicado: tela.c.definirPasta("")
                        }
                        Botao {
                            texto: "Alterar"
                            icone: "pasta"
                            cor: tela.cor
                            habilitado: !tela.compactando
                            onClicado: dialogoPasta.open()
                        }
                    }
                }
                Rotulo {
                    width: parent.width
                    wrapMode: Text.Wrap
                    color: Tema.textoSuave
                    font.pixelSize: 12
                    text: "O original não é alterado. A cópia se chama \"nome (compactado)\" e só é salva se ficar menor."
                }
            }
        }
    }

    FileDialog {
        id: dialogoArquivos
        title: "Escolha os PDFs e imagens para compactar"
        fileMode: FileDialog.OpenFiles
        currentFolder: tela.c.pastaDestinoUrl
        nameFilters: ["PDFs e imagens (*.pdf *.jpg *.jpeg *.png *.webp)", "Todos os arquivos (*)"]
        onAccepted: {
            const urls = []
            for (let i = 0; i < selectedFiles.length; i++)
                urls.push(selectedFiles[i].toString())
            tela.c.adicionarArquivos(urls)
        }
    }

    FolderDialog {
        id: dialogoPasta
        title: "Onde salvar as cópias compactadas"
        currentFolder: tela.c.pastaDestinoUrl
        onAccepted: tela.c.definirPasta(selectedFolder.toString())
    }
}
