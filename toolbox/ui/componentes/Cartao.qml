import QtQuick
import "../tema"

// Bloco de conteúdo com título discreto. Os filhos entram abaixo do título.
Rectangle {
    id: cartao

    property string titulo: ""
    default property alias conteudo: coluna.data

    implicitHeight: coluna.implicitHeight + 36
    radius: 18
    color: Tema.comAlfa(Tema.superficie, 0.82)
    border.width: 1
    border.color: Tema.borda

    Column {
        id: coluna
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 18 }
        spacing: 12

        Text {
            text: cartao.titulo.toUpperCase()
            visible: cartao.titulo !== ""
            color: Tema.textoApagado
            font.family: Tema.fonte
            font.pixelSize: 11
            font.weight: Font.Bold
            font.letterSpacing: 1.6
        }
    }
}
