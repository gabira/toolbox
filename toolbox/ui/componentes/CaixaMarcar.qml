import QtQuick
import "../tema"

Item {
    id: caixa

    property string texto: ""
    property bool marcada: false
    property color cor: Tema.destaque
    property bool habilitada: true
    signal alternada(bool marcada)

    implicitWidth: linha.implicitWidth
    implicitHeight: 28
    opacity: habilitada ? 1 : 0.5

    Row {
        id: linha
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10

        Rectangle {
            width: 22
            height: 22
            radius: 7
            anchors.verticalCenter: parent.verticalCenter
            color: caixa.marcada ? caixa.cor : "transparent"
            border.width: caixa.marcada ? 0 : 1.5
            border.color: area.containsMouse ? caixa.cor : Tema.borda
            Behavior on color { ColorAnimation { duration: Tema.rapida } }

            Icone {
                anchors.centerIn: parent
                nome: "check"
                width: 16
                height: 16
                resolucao: 32
                scale: caixa.marcada ? 1 : 0
                Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutBack } }
            }
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: caixa.texto
            color: Tema.texto
            font.family: Tema.fonte
            font.pixelSize: 14
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        enabled: caixa.habilitada
        cursorShape: Qt.PointingHandCursor
        onClicked: caixa.alternada(!caixa.marcada)
    }
}
