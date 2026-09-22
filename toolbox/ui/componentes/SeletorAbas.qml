import QtQuick
import "../tema"

// Controle segmentado com destaque que desliza entre as opções.
// opcoes: [{ id, nome }]
Rectangle {
    id: seletor

    property var opcoes: []
    property string selecionada: ""
    property color cor: Tema.destaque
    property bool habilitado: true
    signal escolhida(string id)

    readonly property int indiceAtual: {
        for (let i = 0; i < opcoes.length; i++)
            if (opcoes[i].id === selecionada)
                return i
        return 0
    }
    readonly property real larguraOpcao: (width - 8) / Math.max(opcoes.length, 1)

    implicitHeight: 46
    radius: height / 2
    color: Tema.comAlfa(Tema.superficie, 0.9)
    border.width: 1
    border.color: Tema.borda
    opacity: habilitado ? 1 : 0.5

    Rectangle {
        x: 4 + seletor.indiceAtual * seletor.larguraOpcao
        y: 4
        width: seletor.larguraOpcao
        height: parent.height - 8
        radius: height / 2
        color: Tema.comAlfa(seletor.cor, 0.85)
        layer.enabled: true
        layer.effect: Brilho { cor: seletor.cor; intensidade: 0.55 }

        Behavior on x { NumberAnimation { duration: 280; easing.type: Easing.OutCubic } }
    }

    Row {
        x: 4
        y: 4
        Repeater {
            model: seletor.opcoes
            delegate: Item {
                required property var modelData
                required property int index
                width: seletor.larguraOpcao
                height: seletor.height - 8

                Text {
                    anchors.centerIn: parent
                    text: parent.modelData.nome
                    color: parent.index === seletor.indiceAtual ? "white" : Tema.textoSuave
                    font.family: Tema.fonte
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    Behavior on color { ColorAnimation { duration: Tema.rapida } }
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: seletor.habilitado
                    cursorShape: Qt.PointingHandCursor
                    onClicked: seletor.escolhida(parent.modelData.id)
                }
            }
        }
    }
}
