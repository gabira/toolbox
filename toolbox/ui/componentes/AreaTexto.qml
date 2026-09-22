import QtQuick
import "../tema"

// Campo de texto de várias linhas com rolagem, dica e brilho no foco.
Rectangle {
    id: area

    property alias texto: edicao.text
    property alias edicao: edicao
    property string dica: ""
    property color cor: Tema.destaque
    property bool habilitado: true
    signal editado(string texto)

    implicitHeight: 130
    radius: 12
    opacity: habilitado ? 1 : 0.5
    color: Tema.comAlfa(Tema.fundo, 0.55)
    border.width: edicao.activeFocus ? 2 : 1
    border.color: edicao.activeFocus ? cor : Tema.borda

    Behavior on border.color { ColorAnimation { duration: Tema.rapida } }

    Flickable {
        id: rolagem
        anchors.fill: parent
        anchors.margins: 12
        contentWidth: width
        contentHeight: edicao.contentHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        // Mantém o cursor visível ao digitar ou colar muitas linhas.
        function garantirVisivel(r) {
            if (contentY >= r.y)
                contentY = r.y
            else if (contentY + height <= r.y + r.height)
                contentY = r.y + r.height - height
        }

        TextEdit {
            id: edicao
            width: rolagem.width
            height: Math.max(rolagem.height, contentHeight)
            enabled: area.habilitado
            wrapMode: TextEdit.WrapAnywhere
            selectByMouse: true
            color: Tema.texto
            selectionColor: Tema.comAlfa(area.cor, 0.6)
            selectedTextColor: "white"
            font.family: Tema.fonte
            font.pixelSize: 14
            onTextChanged: if (activeFocus) area.editado(text)
            onCursorRectangleChanged: rolagem.garantirVisivel(cursorRectangle)

            Text {
                visible: edicao.text === ""
                width: parent.width
                text: area.dica
                color: Tema.textoApagado
                wrapMode: Text.Wrap
                font: edicao.font
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        z: -1
        cursorShape: Qt.IBeamCursor
        onClicked: edicao.forceActiveFocus()
    }
}
