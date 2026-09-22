import QtQuick
import "../tema"

// Campo de texto de uma linha, com dica, sufixo opcional (ex.: ".m4a") e brilho no foco.
Rectangle {
    id: campo

    property alias texto: entrada.text
    property alias entrada: entrada
    property string dica: ""
    property string sufixo: ""
    property color cor: Tema.destaque
    property bool habilitado: true
    signal editado(string texto)
    signal confirmado()

    implicitHeight: 44
    radius: 12
    opacity: habilitado ? 1 : 0.5
    color: Tema.comAlfa(Tema.fundo, 0.55)
    border.width: entrada.activeFocus ? 2 : 1
    border.color: entrada.activeFocus ? cor : (areaCampo.containsMouse ? Tema.comAlfa(cor, 0.6) : Tema.borda)

    Behavior on border.color { ColorAnimation { duration: Tema.rapida } }

    MouseArea {
        id: areaCampo
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.IBeamCursor
        onClicked: entrada.forceActiveFocus()
    }

    TextInput {
        id: entrada
        anchors {
            left: parent.left; leftMargin: 14
            right: rotuloSufixo.visible ? rotuloSufixo.left : parent.right
            rightMargin: rotuloSufixo.visible ? 4 : 14
            verticalCenter: parent.verticalCenter
        }
        enabled: campo.habilitado
        clip: true
        selectByMouse: true
        color: Tema.texto
        selectionColor: Tema.comAlfa(campo.cor, 0.6)
        selectedTextColor: "white"
        font.family: Tema.fonte
        font.pixelSize: 15
        onTextEdited: campo.editado(text)
        onAccepted: campo.confirmado()

        Text {
            anchors.fill: parent
            verticalAlignment: Text.AlignVCenter
            visible: entrada.text === ""
            text: campo.dica
            color: Tema.textoApagado
            elide: Text.ElideRight
            font: entrada.font
        }
    }

    Text {
        id: rotuloSufixo
        anchors.right: parent.right
        anchors.rightMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        visible: campo.sufixo !== ""
        text: campo.sufixo
        color: Tema.textoSuave
        font.family: Tema.fonte
        font.pixelSize: 15
    }
}
