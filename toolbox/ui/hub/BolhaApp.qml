import QtQuick
import "../tema"
import "../componentes"

// Bolha de um app ao redor do hub.
Item {
    id: bolha

    property var app: ({})
    property bool interativa: true
    signal clicada()

    readonly property color cor: app.cor || Tema.destaque
    readonly property bool emFoco: area.containsMouse && interativa

    Item {
        anchors.fill: parent
        scale: bolha.emFoco ? 1.07 : 1
        Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }

        Rectangle {
            anchors.fill: parent
            radius: width / 2
            gradient: Gradient {
                GradientStop { position: 0; color: Tema.misturar(Tema.fundo, bolha.cor, 0.55) }
                GradientStop { position: 1; color: Tema.misturar(Tema.fundo, bolha.cor, 0.2) }
            }
            border.width: Math.max(2, width * 0.022)
            border.color: Qt.lighter(bolha.cor, 1.2)
            layer.enabled: true
            layer.effect: Brilho { cor: bolha.cor; intensidade: bolha.emFoco ? 1 : 0.7 }
        }

        Column {
            anchors.centerIn: parent
            spacing: bolha.height * 0.04

            Icone {
                anchors.horizontalCenter: parent.horizontalCenter
                fonte: bolha.app.icone || ""
                resolucao: 96
                width: bolha.width * 0.3
                height: width
            }
            Text {
                width: bolha.width * 0.78
                horizontalAlignment: Text.AlignHCenter
                text: bolha.app.nome || ""
                color: Tema.texto
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
                font.family: Tema.fonte
                font.pixelSize: Math.max(1, bolha.width * 0.1)
                font.weight: Font.Bold
            }
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        enabled: bolha.interativa
        cursorShape: Qt.PointingHandCursor
        onClicked: (evento) => {
            const dx = evento.x - width / 2, dy = evento.y - height / 2
            if (dx * dx + dy * dy <= width * width / 4)
                bolha.clicada()
        }
    }
}
