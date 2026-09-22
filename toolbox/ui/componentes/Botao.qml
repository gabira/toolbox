import QtQuick
import "../tema"

Rectangle {
    id: botao

    property string texto: ""
    property string icone: ""       // nome de um ícone da UI (ui/icones)
    property url iconeFonte: ""     // ou uma imagem qualquer (ex.: o logo)
    property color cor: Tema.destaque
    property bool primario: false
    property bool habilitado: true
    signal clicado()

    implicitHeight: 44
    implicitWidth: conteudo.implicitWidth + 40
    radius: height / 2
    opacity: habilitado ? 1 : 0.4
    scale: area.pressed ? 0.97 : 1

    color: primario
           ? (area.containsMouse ? Qt.lighter(cor, 1.12) : cor)
           : (area.containsMouse ? Tema.comAlfa(cor, 0.16) : "transparent")
    border.width: primario ? 0 : 1.5
    border.color: Tema.comAlfa(cor, area.containsMouse ? 0.95 : 0.55)

    layer.enabled: primario && habilitado
    layer.effect: Brilho { cor: botao.cor; intensidade: area.containsMouse ? 0.9 : 0.5 }

    Behavior on color { ColorAnimation { duration: Tema.rapida } }
    Behavior on scale { NumberAnimation { duration: 120 } }
    Behavior on opacity { NumberAnimation { duration: Tema.rapida } }

    Row {
        id: conteudo
        anchors.centerIn: parent
        spacing: 8

        Icone {
            nome: botao.icone
            fonte: botao.iconeFonte
            visible: botao.icone !== "" || botao.iconeFonte.toString() !== ""
            width: 18
            height: 18
            resolucao: 36
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: botao.texto
            color: Tema.texto
            font.family: Tema.fonte
            font.pixelSize: 15
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        enabled: botao.habilitado
        cursorShape: Qt.PointingHandCursor
        onClicked: botao.clicado()
    }
}
