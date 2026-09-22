import QtQuick
import "../tema"

Item {
    id: barra

    property real valor: 0          // 0..1
    property color cor: Tema.destaque

    implicitHeight: 10

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: Tema.comAlfa(barra.cor, 0.15)
    }

    Rectangle {
        height: parent.height
        width: Math.max(height, parent.width * Math.min(1, barra.valor))
        visible: barra.valor > 0
        radius: height / 2
        color: barra.cor
        layer.enabled: true
        layer.effect: Brilho { cor: barra.cor; intensidade: 0.7 }

        Behavior on width { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    }
}
