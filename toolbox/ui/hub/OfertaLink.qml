import QtQuick
import "../tema"
import "../componentes"

// Aviso no canto: "encontrei um link do YouTube copiado, quer usar?"
Rectangle {
    id: oferta

    property bool mostrar: false
    property string link: ""
    property string resumo: ""
    signal usar()
    signal ignorar()

    readonly property color cor: "#EF4444"

    width: 360
    height: coluna.implicitHeight + 32
    radius: 18
    color: Tema.comAlfa(Tema.superficie, 0.97)
    border.width: 1
    border.color: Tema.comAlfa(cor, 0.55)
    opacity: mostrar ? 1 : 0
    visible: opacity > 0
    transform: Translate {
        x: oferta.mostrar ? 0 : 40
        Behavior on x { NumberAnimation { duration: 320; easing.type: Easing.OutCubic } }
    }

    layer.enabled: visible
    layer.effect: Brilho { cor: oferta.cor; intensidade: 0.45 }

    Behavior on opacity { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }

    Column {
        id: coluna
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
        spacing: 12

        Row {
            spacing: 12
            Rectangle {
                width: 40
                height: 40
                radius: 12
                color: Tema.comAlfa(oferta.cor, 0.22)
                Icone { anchors.centerIn: parent; nome: "link"; width: 20; height: 20; resolucao: 40 }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text {
                    text: "Link copiado"
                    color: Tema.texto
                    font.family: Tema.fonte
                    font.pixelSize: 15
                    font.weight: Font.Bold
                }
                Text {
                    text: "Encontrei um " + oferta.resumo + " na área de transferência."
                    width: coluna.width - 52
                    wrapMode: Text.Wrap
                    color: Tema.textoSuave
                    font.family: Tema.fonte
                    font.pixelSize: 12
                }
            }
        }

        Text {
            width: parent.width
            text: oferta.link
            elide: Text.ElideMiddle
            color: Tema.textoApagado
            font.family: Tema.fonte
            font.pixelSize: 12
        }

        Row {
            spacing: 8
            Botao {
                height: 38
                primario: true
                cor: oferta.cor
                texto: "Usar link"
                onClicado: oferta.usar()
            }
            Botao {
                height: 38
                texto: "Agora não"
                cor: Tema.textoSuave
                onClicado: oferta.ignorar()
            }
        }
    }
}
