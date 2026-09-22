import QtQuick
import QtQuick.Dialogs
import "../../ui/tema"
import "../../ui/componentes"

Item {
    id: tela

    property var controlador
    property color cor: Tema.destaque

    readonly property var c: controlador
    readonly property bool gravando: c.estado === "gravando"
    readonly property bool salvando: c.estado === "salvando"
    readonly property bool ocupado: gravando || salvando
    readonly property bool temFonte: c.gravarMicrofone || c.gravarSistema

    Component.onCompleted: c.atualizarDispositivos()

    component Rotulo: Text {
        color: Tema.texto
        font.family: Tema.fonte
        font.pixelSize: 15
    }

    // Medidor de nível de uma fonte (pico em escala de dB, -60 a 0).
    component Medidor: Item {
        id: medidor
        property string titulo: ""
        property string icone: ""
        property real nivel: 0
        property bool ativo: true
        readonly property real fracao: nivel <= 0.001 ? 0 : Math.max(0, Math.min(1, (20 * Math.log(nivel) / Math.LN10 + 60) / 60))

        height: 40
        opacity: ativo ? 1 : 0.4

        Icone {
            id: iconeMedidor
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            nome: medidor.icone
            width: 22
            height: 22
        }
        Rotulo {
            id: tituloMedidor
            anchors { left: iconeMedidor.right; leftMargin: 10; verticalCenter: parent.verticalCenter }
            width: 110
            text: medidor.titulo
            font.pixelSize: 14
        }
        Rectangle {
            anchors { left: tituloMedidor.right; right: parent.right; verticalCenter: parent.verticalCenter }
            height: 10
            radius: 5
            color: Tema.comAlfa(tela.cor, 0.14)

            Rectangle {
                height: parent.height
                radius: 5
                width: parent.width * medidor.fracao
                color: medidor.fracao > 0.95 ? Tema.erro : tela.cor
                Behavior on width { NumberAnimation { duration: 70 } }
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
            width: Math.min(680, tela.width - 64)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 14

            // --- Gravar ---
            Cartao {
                width: parent.width

                Item {
                    width: parent.width
                    height: 150

                    // Botão redondo: círculo = gravar, quadrado = parar
                    Item {
                        id: botaoGravar
                        width: 112
                        height: 112
                        anchors.verticalCenter: parent.verticalCenter
                        opacity: (tela.temFonte || tela.gravando) && !tela.salvando ? 1 : 0.4

                        Rectangle {
                            id: pulso
                            anchors.centerIn: parent
                            width: parent.width
                            height: width
                            radius: width / 2
                            color: "transparent"
                            border.width: 3
                            border.color: tela.cor
                            opacity: 0
                            visible: tela.gravando
                            SequentialAnimation on scale {
                                running: tela.gravando
                                loops: Animation.Infinite
                                NumberAnimation { from: 1; to: 1.25; duration: 1100; easing.type: Easing.OutCubic }
                            }
                            SequentialAnimation on opacity {
                                running: tela.gravando
                                loops: Animation.Infinite
                                NumberAnimation { from: 0.7; to: 0; duration: 1100; easing.type: Easing.OutCubic }
                            }
                        }
                        Rectangle {
                            anchors.fill: parent
                            radius: width / 2
                            color: Tema.comAlfa(tela.cor, areaGravar.containsMouse ? 0.3 : 0.2)
                            border.width: 2
                            border.color: tela.cor
                            layer.enabled: true
                            layer.effect: Brilho { cor: tela.cor; intensidade: tela.gravando ? 1 : 0.6 }
                        }
                        Rectangle {
                            anchors.centerIn: parent
                            width: tela.gravando ? 34 : 46
                            height: width
                            radius: tela.gravando ? 8 : width / 2
                            color: tela.cor
                            Behavior on width { NumberAnimation { duration: Tema.rapida } }
                            Behavior on radius { NumberAnimation { duration: Tema.rapida } }
                        }
                        MouseArea {
                            id: areaGravar
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: !tela.salvando && (tela.gravando || tela.temFonte)
                            cursorShape: Qt.PointingHandCursor
                            onClicked: tela.gravando ? tela.c.parar() : tela.c.gravar()
                        }
                    }

                    Column {
                        anchors {
                            left: botaoGravar.right; leftMargin: 26
                            right: parent.right
                            verticalCenter: parent.verticalCenter
                        }
                        spacing: 4

                        Rotulo {
                            text: tela.c.tempo
                            font.pixelSize: 40
                            font.weight: Font.Bold
                            font.features: { "tnum": 1 }
                            color: tela.gravando ? Tema.texto : Tema.textoSuave
                        }
                        Rotulo {
                            width: parent.width
                            wrapMode: Text.Wrap
                            color: Tema.textoSuave
                            font.pixelSize: 13
                            text: tela.salvando ? "Salvando a gravação…"
                                : tela.gravando ? "Gravando. Clique para parar e salvar."
                                : tela.c.estado === "concluido" ? "Pronto. Clique para uma nova gravação."
                                : tela.temFonte ? "Clique no botão para começar a gravar."
                                : "Ative o microfone ou o som do computador abaixo."
                        }
                    }
                }

                Medidor {
                    width: parent.width
                    titulo: "Você"
                    icone: "microfone"
                    nivel: tela.c.nivelMicrofone
                    ativo: tela.c.gravarMicrofone
                }
                Medidor {
                    width: parent.width
                    titulo: "Computador"
                    icone: "som"
                    nivel: tela.c.nivelSistema
                    ativo: tela.c.gravarSistema
                }
            }

            // --- Resultado ---
            Rectangle {
                readonly property bool sucesso: tela.c.estado === "concluido"
                readonly property color corResultado: sucesso ? Tema.sucesso : Tema.erro

                width: parent.width
                height: Math.max(64, textoResultado.implicitHeight + 28)
                radius: 16
                visible: sucesso || tela.c.estado === "erro" || (tela.c.mensagem !== "" && !tela.ocupado)
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
                        texto: "Ouvir"
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

            // --- Fontes ---
            Cartao {
                titulo: "O que gravar"
                width: parent.width

                Item {
                    width: parent.width
                    height: 28
                    CaixaMarcar {
                        anchors.verticalCenter: parent.verticalCenter
                        texto: "Meu microfone"
                        marcada: tela.c.gravarMicrofone
                        cor: tela.cor
                        habilitada: !tela.ocupado && tela.c.microfones.length > 0
                        onAlternada: (valor) => tela.c.ativarMicrofone(valor)
                    }
                    Botao {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        texto: "Atualizar"
                        cor: tela.cor
                        habilitado: !tela.ocupado
                        onClicado: tela.c.atualizarDispositivos()
                    }
                }
                Rotulo {
                    visible: tela.c.microfones.length === 0
                    width: parent.width
                    wrapMode: Text.Wrap
                    color: Tema.textoSuave
                    font.pixelSize: 13
                    text: "Nenhum microfone encontrado. Conecte um e clique em Atualizar."
                }
                Repeater {
                    model: tela.c.microfones.length > 1 && tela.c.gravarMicrofone ? tela.c.microfones : []
                    OpcaoSelecao {
                        required property var modelData
                        width: parent.width
                        implicitHeight: 48
                        titulo: modelData.nome
                        selo: modelData.padrao ? "Padrão" : ""
                        cor: tela.cor
                        selecionada: modelData.selecionado
                        habilitada: !tela.ocupado
                        onClicada: tela.c.escolherMicrofone(modelData.nome)
                    }
                }

                CaixaMarcar {
                    texto: "Som do computador (participantes, vídeos, música)"
                    marcada: tela.c.gravarSistema
                    cor: tela.cor
                    habilitada: !tela.ocupado && tela.c.saidas.length > 0
                    onAlternada: (valor) => tela.c.ativarSistema(valor)
                }
                Repeater {
                    model: tela.c.saidas.length > 1 && tela.c.gravarSistema ? tela.c.saidas : []
                    OpcaoSelecao {
                        required property var modelData
                        width: parent.width
                        implicitHeight: 48
                        titulo: modelData.nome
                        selo: modelData.padrao ? "Padrão" : ""
                        cor: tela.cor
                        selecionada: modelData.selecionado
                        habilitada: !tela.ocupado
                        onClicada: tela.c.escolherSaida(modelData.nome)
                    }
                }

                Row {
                    visible: tela.c.gravarMicrofone && tela.c.gravarSistema
                    width: parent.width
                    spacing: 10
                    Icone { nome: "alerta"; width: 18; height: 18; anchors.verticalCenter: parent.verticalCenter }
                    Rotulo {
                        width: parent.width - 28
                        wrapMode: Text.Wrap
                        color: Tema.textoSuave
                        font.pixelSize: 12
                        text: "Use fones de ouvido: com caixa de som o microfone também capta os participantes e eles saem com eco."
                    }
                }
            }

            // --- Formato ---
            Cartao {
                titulo: "Formato"
                width: parent.width

                Grid {
                    id: grade
                    width: parent.width
                    columns: 3
                    spacing: 10

                    Repeater {
                        model: tela.c.formatos
                        OpcaoSelecao {
                            required property var modelData
                            width: (grade.width - grade.spacing * 2) / 3
                            titulo: modelData.nome
                            subtitulo: modelData.descricao
                            selo: modelData.selo
                            cor: tela.cor
                            selecionada: tela.c.formato === modelData.id
                            habilitada: !tela.ocupado
                            onClicada: tela.c.definirFormato(modelData.id)
                        }
                    }
                }
            }

            // --- Saída ---
            Cartao {
                titulo: "Saída"
                width: parent.width

                Rotulo {
                    text: "Nome do arquivo"
                    color: Tema.textoSuave
                    font.pixelSize: 13
                }
                CampoTexto {
                    width: parent.width
                    texto: tela.c.nomeSaida
                    dica: "Gravação"
                    sufixo: "." + tela.c.extensaoSaida
                    cor: tela.cor
                    habilitado: !tela.salvando
                    onEditado: (texto) => tela.c.definirNome(texto)
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
                        habilitado: !tela.salvando
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

        }
    }

    FolderDialog {
        id: dialogoPasta
        title: "Onde salvar a gravação"
        currentFolder: tela.c.pastaDestinoUrl
        onAccepted: tela.c.definirPasta(selectedFolder.toString())
    }
}
