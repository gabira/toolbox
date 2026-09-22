import QtQuick
import QtQuick.Effects
import QtQuick.Dialogs
import "../../ui/tema"
import "../../ui/componentes"

Item {
    id: tela

    property var controlador
    property color cor: Tema.destaque

    readonly property var c: controlador
    readonly property var info: c.info
    readonly property bool temInfo: info.titulo !== undefined
    readonly property bool baixandoUnico: c.estado === "baixando"
    readonly property bool rodandoLote: c.estadoLote === "rodando"
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

    component Rotulo: Text {
        color: Tema.texto
        font.family: Tema.fonte
        font.pixelSize: 15
    }

    // Barra "indeterminada" para quando ainda não há porcentagem
    component BarraIndeterminada: Rectangle {
        id: barraInd
        height: 6
        radius: 3
        clip: true
        color: Tema.comAlfa(tela.cor, 0.15)
        Rectangle {
            width: barraInd.width * 0.3
            height: parent.height
            radius: 3
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

    component LinhaPasta: Cartao {
        titulo: "Salvar em"
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
                habilitado: !tela.c.ocupado
                onClicado: dialogoPasta.open()
            }
        }
    }

    // Porcentagem + barra + botão de parar
    component LinhaProgresso: Item {
        property string textoParar: "Cancelar"
        height: 56
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
                right: botaoParar.left; rightMargin: 16
                verticalCenter: parent.verticalCenter
            }
            valor: tela.c.progresso
            cor: tela.cor
        }
        Botao {
            id: botaoParar
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            texto: parent.textoParar
            cor: Tema.erro
            onClicado: tela.c.cancelar()
        }
    }

    // Ao iniciar a fila, rola até o progresso para mostrar a lista andando.
    Connections {
        target: tela.c
        function onAlterado() {
            if (tela.rodandoLote && !tela._rolouParaFila) {
                tela._rolouParaFila = true
                Qt.callLater(rolagem.mostrar, acoesLote)
            } else if (!tela.rodandoLote) {
                tela._rolouParaFila = false
            }
        }
    }
    property bool _rolouParaFila: false

    Flickable {
        id: rolagem
        anchors.fill: parent
        contentHeight: coluna.height + 40
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        function mostrar(item) {
            const y = item.mapToItem(coluna, 0, 0).y - 16
            animRolagem.to = Math.max(0, Math.min(y, contentHeight - height))
            animRolagem.start()
        }

        NumberAnimation {
            id: animRolagem
            target: rolagem
            property: "contentY"
            duration: 450
            easing.type: Easing.OutCubic
        }

        Column {
            id: coluna
            width: Math.min(720, tela.width - 64)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 14

            SeletorAbas {
                width: parent.width
                opcoes: [{ id: "unico", nome: "Um vídeo" }, { id: "lote", nome: "Vários vídeos" }]
                selecionada: tela.c.aba
                cor: tela.cor
                habilitado: !tela.c.ocupado
                onEscolhida: (id) => tela.c.definirAba(id)
            }

            // ================================================== UM VÍDEO
            Column {
                width: parent.width
                spacing: 14
                visible: tela.c.aba === "unico"

                Cartao {
                    titulo: "Link do vídeo ou playlist"
                    width: parent.width

                    Item {
                        width: parent.width
                        height: 44

                        CampoTexto {
                            id: campoLink
                            anchors {
                                left: parent.left
                                right: botaoColar.left; rightMargin: 10
                                verticalCenter: parent.verticalCenter
                            }
                            dica: "https://www.youtube.com/watch?v=…"
                            cor: tela.cor
                            habilitado: !tela.c.ocupado
                            Component.onCompleted: texto = tela.c.link
                            onEditado: (texto) => tela.c.definirLink(texto)
                            onConfirmado: tela.c.analisarLink()
                        }
                        Botao {
                            id: botaoColar
                            anchors.right: botaoAnalisar.left
                            anchors.rightMargin: 10
                            anchors.verticalCenter: parent.verticalCenter
                            texto: "Colar"
                            icone: "colar"
                            cor: tela.cor
                            habilitado: !tela.c.ocupado
                            onClicado: {
                                campoLink.entrada.selectAll()
                                campoLink.entrada.paste()
                                tela.c.definirLink(campoLink.texto)
                                tela.c.analisarLink()
                            }
                        }
                        Botao {
                            id: botaoAnalisar
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            primario: true
                            texto: tela.c.estado === "analisando" ? "Analisando…" : "Analisar"
                            cor: tela.cor
                            habilitado: !tela.c.ocupado
                            onClicado: tela.c.analisarLink()
                        }
                    }
                }

                Cartao {
                    titulo: "Vídeo"
                    width: parent.width
                    visible: tela.c.estado === "analisando" || tela.temInfo

                    Column {
                        visible: tela.c.estado === "analisando"
                        width: parent.width
                        spacing: 12
                        Rotulo { text: "Consultando o YouTube…"; color: Tema.textoSuave }
                        BarraIndeterminada { width: parent.width }
                    }

                    Item {
                        visible: tela.temInfo
                        width: parent.width
                        height: miniatura.height

                        // Miniatura com cantos arredondados
                        Item {
                            id: miniatura
                            width: 176
                            height: 99

                            Rectangle {
                                anchors.fill: parent
                                radius: 12
                                color: Tema.comAlfa(tela.cor, 0.15)
                                Icone { anchors.centerIn: parent; nome: "video"; width: 28; height: 28; opacity: 0.6 }
                            }
                            Image {
                                id: imagem
                                anchors.fill: parent
                                source: tela.info.miniatura || ""
                                fillMode: Image.PreserveAspectCrop
                                asynchronous: true
                                visible: false
                            }
                            MultiEffect {
                                anchors.fill: parent
                                source: imagem
                                visible: imagem.status === Image.Ready
                                maskEnabled: true
                                maskSource: mascara
                                maskThresholdMin: 0.5
                                maskSpreadAtMin: 1.0
                            }
                            Item {
                                id: mascara
                                anchors.fill: parent
                                layer.enabled: true
                                visible: false
                                Rectangle { anchors.fill: parent; radius: 12; color: "black" }
                            }
                        }

                        Column {
                            anchors {
                                left: miniatura.right; leftMargin: 16
                                right: parent.right
                                verticalCenter: parent.verticalCenter
                            }
                            spacing: 6
                            Rotulo {
                                width: parent.width
                                text: tela.info.titulo || ""
                                wrapMode: Text.Wrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                                font.pixelSize: 16
                                font.weight: Font.DemiBold
                            }
                            Rotulo {
                                width: parent.width
                                color: Tema.textoSuave
                                font.pixelSize: 13
                                elide: Text.ElideRight
                                text: {
                                    const partes = []
                                    if (tela.info.canal) partes.push(tela.info.canal)
                                    if (tela.info.e_playlist) partes.push("Playlist com " + tela.info.n_itens + " vídeos")
                                    else if (tela.info.duracao) partes.push(tela.info.duracao)
                                    return partes.join(" · ")
                                }
                            }
                            CaixaMarcar {
                                visible: tela.info.e_playlist === true
                                texto: "Baixar a playlist inteira (" + (tela.info.n_itens || 0) + " vídeos)"
                                marcada: tela.c.baixarPlaylist
                                cor: tela.cor
                                habilitada: !tela.c.ocupado
                                onAlternada: (valor) => tela.c.definirPlaylist(valor)
                            }
                        }
                    }
                }

                Cartao {
                    titulo: "Qualidade"
                    width: parent.width
                    visible: tela.temInfo

                    Grid {
                        id: gradeQualidade
                        width: parent.width
                        columns: 3
                        spacing: 10
                        Repeater {
                            model: tela.c.opcoesQualidade
                            OpcaoSelecao {
                                required property var modelData
                                width: (gradeQualidade.width - 2 * gradeQualidade.spacing) / 3
                                implicitHeight: 58
                                titulo: modelData.nome
                                subtitulo: modelData.descricao
                                cor: tela.cor
                                selecionada: tela.c.qualidade === modelData.id
                                habilitada: !tela.c.ocupado
                                onClicada: tela.c.definirQualidade(modelData.id)
                            }
                        }
                    }
                }

                LinhaPasta { width: parent.width; visible: tela.temInfo }

                Item {
                    width: parent.width
                    height: 56
                    visible: tela.temInfo

                    Botao {
                        anchors.fill: parent
                        primario: true
                        cor: tela.cor
                        texto: tela.info.e_playlist && tela.c.baixarPlaylist ? "Baixar playlist" : "Baixar"
                        icone: "seta"
                        habilitado: !tela.c.ocupado
                        visible: !tela.baixandoUnico
                        onClicado: tela.c.baixarUnico()
                    }
                    LinhaProgresso {
                        anchors.fill: parent
                        visible: tela.baixandoUnico
                    }
                }

                Rotulo {
                    visible: tela.baixandoUnico && tela.c.textoProgresso !== ""
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    color: Tema.textoSuave
                    font.pixelSize: 13
                    text: tela.c.textoProgresso
                }

                // Resultado
                Rectangle {
                    readonly property bool sucesso: tela.c.estado === "concluido"
                    readonly property color corResultado: sucesso ? Tema.sucesso
                                                                  : (tela.c.estado === "erro" ? Tema.erro : Tema.textoSuave)
                    width: parent.width
                    height: 64
                    radius: 16
                    visible: tela.c.mensagem !== "" && !tela.baixandoUnico && tela.c.estado !== "analisando"
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
                            right: botoesResultado.left; rightMargin: 12
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
                            // O vídeo baixado vira o arquivo da TOOLBOX (ex.: para separar o áudio).
                            visible: tela.c.arquivoBaixado !== ""
                            texto: "Usar na TOOLBOX"
                            iconeFonte: Tema.imagem("logo_simbolo")
                            cor: Tema.destaque
                            onClicado: nucleo.definirArquivo(tela.c.arquivoBaixado)
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

            // ================================================== VÁRIOS VÍDEOS
            Column {
                width: parent.width
                spacing: 14
                visible: tela.c.aba === "lote"

                Cartao {
                    titulo: "Links — um por linha"
                    width: parent.width

                    AreaTexto {
                        id: areaLinks
                        width: parent.width
                        height: 140
                        dica: "Cole aqui os links dos vídeos ou playlists, um por linha…"
                        cor: tela.cor
                        habilitado: !tela.rodandoLote
                        Component.onCompleted: texto = tela.c.textoLinks
                        onEditado: (texto) => tela.c.definirTextoLinks(texto)
                    }

                    Item {
                        width: parent.width
                        height: 40
                        Rotulo {
                            anchors.verticalCenter: parent.verticalCenter
                            color: Tema.textoSuave
                            font.pixelSize: 13
                            text: tela.c.totalLinks === 0 ? "Nenhum link ainda."
                                  : tela.c.totalLinks === 1 ? "1 link detectado."
                                  : tela.c.totalLinks + " links detectados."
                        }
                        Botao {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            texto: "Colar"
                            icone: "colar"
                            cor: tela.cor
                            habilitado: !tela.rodandoLote
                            onClicado: {
                                const edicao = areaLinks.edicao
                                edicao.forceActiveFocus()
                                edicao.cursorPosition = edicao.length
                                if (edicao.length > 0 && !edicao.text.endsWith("\n"))
                                    edicao.insert(edicao.length, "\n")
                                edicao.paste()
                            }
                        }
                    }
                }

                Cartao {
                    titulo: "Qualidade (vale para todos)"
                    width: parent.width

                    Grid {
                        id: gradeLote
                        width: parent.width
                        columns: 3
                        spacing: 10
                        Repeater {
                            model: tela.c.opcoesLote
                            OpcaoSelecao {
                                required property var modelData
                                width: (gradeLote.width - 2 * gradeLote.spacing) / 3
                                implicitHeight: 58
                                titulo: modelData.nome
                                subtitulo: modelData.descricao
                                cor: tela.cor
                                selecionada: tela.c.qualidadeLote === modelData.id
                                habilitada: !tela.c.ocupado
                                onClicada: tela.c.definirQualidadeLote(modelData.id)
                            }
                        }
                    }
                    Rotulo {
                        width: parent.width
                        wrapMode: Text.Wrap
                        color: Tema.textoApagado
                        font.pixelSize: 12
                        text: "Cada vídeo tem resoluções diferentes, então a qualidade funciona como um teto: \"1080p\" = 1080p ou o melhor abaixo disso."
                    }
                }

                LinhaPasta { width: parent.width }

                Item {
                    id: acoesLote
                    width: parent.width
                    height: 56

                    Row {
                        anchors.fill: parent
                        spacing: 10
                        visible: !tela.rodandoLote
                        Botao {
                            width: parent.width - botaoConferir.width - parent.spacing
                            height: parent.height
                            primario: true
                            cor: tela.cor
                            texto: "Baixar todos"
                            icone: "seta"
                            habilitado: !tela.c.ocupado && tela.c.totalLinks > 0
                            onClicado: tela.c.iniciarLote(false)
                        }
                        Botao {
                            id: botaoConferir
                            height: parent.height
                            texto: "Só conferir"
                            cor: tela.cor
                            habilitado: !tela.c.ocupado && tela.c.totalLinks > 0
                            onClicado: tela.c.iniciarLote(true)
                        }
                    }
                    LinhaProgresso {
                        anchors.fill: parent
                        visible: tela.rodandoLote
                        textoParar: "Parar"
                    }
                }

                Rotulo {
                    visible: tela.c.statusLote !== ""
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                    color: tela.corTom(tela.c.tomStatusLote)
                    font.pixelSize: 13
                    text: tela.c.statusLote + (tela.rodandoLote && tela.c.textoProgresso !== "" ? "  ·  " + tela.c.textoProgresso : "")
                }

                Cartao {
                    titulo: "Fila"
                    width: parent.width
                    visible: repetidorFila.count > 0

                    Repeater {
                        id: repetidorFila
                        model: tela.c.fila

                        delegate: Item {
                            id: itemFila
                            required property int index
                            required property string link
                            required property string titulo
                            required property string estado
                            required property string tom
                            required property real progresso

                            width: parent ? parent.width : 0
                            height: 46

                            Rotulo {
                                id: numero
                                width: 28
                                anchors.verticalCenter: parent.verticalCenter
                                color: Tema.textoApagado
                                font.pixelSize: 13
                                text: (itemFila.index + 1) + "."
                            }
                            Column {
                                anchors {
                                    left: numero.right
                                    right: rotuloEstado.left; rightMargin: 12
                                    verticalCenter: parent.verticalCenter
                                }
                                spacing: 5
                                Rotulo {
                                    width: parent.width
                                    elide: Text.ElideMiddle
                                    font.pixelSize: 14
                                    text: itemFila.titulo !== "" ? itemFila.titulo : itemFila.link
                                }
                                BarraProgresso {
                                    width: parent.width
                                    height: 4
                                    visible: itemFila.progresso >= 0 && itemFila.progresso < 1 && itemFila.tom === "ativo"
                                    valor: itemFila.progresso
                                    cor: tela.cor
                                }
                            }
                            Rotulo {
                                id: rotuloEstado
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                width: Math.min(implicitWidth, 220)
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideRight
                                font.pixelSize: 13
                                color: tela.corTom(itemFila.tom)
                                text: itemFila.tom === "ativo" && itemFila.progresso >= 0 && itemFila.progresso < 1
                                      ? Math.round(itemFila.progresso * 100) + "%" : itemFila.estado
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
                }
            }

            // ================================================== MOTOR
            Item {
                width: parent.width
                height: 44

                Rotulo {
                    anchors {
                        left: parent.left
                        right: botaoMotor.left; rightMargin: 12
                        verticalCenter: parent.verticalCenter
                    }
                    elide: Text.ElideRight
                    color: Tema.textoApagado
                    font.pixelSize: 12
                    text: "Motor de download: yt-dlp " + tela.c.versaoMotor
                          + (tela.c.mensagemMotor !== "" ? "  ·  " + tela.c.mensagemMotor
                                                         : "  ·  se parar de baixar, atualize o motor")
                }
                Botao {
                    id: botaoMotor
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    height: 36
                    texto: tela.c.atualizandoMotor ? "Atualizando…" : "Atualizar motor"
                    cor: Tema.textoSuave
                    habilitado: !tela.c.atualizandoMotor && !tela.c.ocupado
                    onClicado: tela.c.atualizarMotor()
                }
            }
        }
    }

    FolderDialog {
        id: dialogoPasta
        title: "Onde salvar os vídeos"
        currentFolder: tela.c.pastaDestinoUrl
        onAccepted: tela.c.definirPasta(selectedFolder.toString())
    }
}
