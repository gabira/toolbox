import QtQuick
import QtQuick.Window
import "tema"
import "hub"

Window {
    width: 1120
    height: 840
    minimumWidth: 820
    minimumHeight: 680
    visible: true
    title: "TOOLBOX"
    color: Tema.fundo

    Hub {
        objectName: "hub"
        anchors.fill: parent
    }
}
