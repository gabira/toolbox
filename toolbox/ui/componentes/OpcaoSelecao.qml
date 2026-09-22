import QtQuick
import "../tema"

// Opção clicável de uma escolha única (ex.: formato de saída).
Rectangle {
    id: opcao

    property string titulo: ""
    property string subtitulo: ""
    property string selo: ""
    property bool selecionada: false
    property bool habilitada: true
    property color cor: Tema.destaque
    signal clicada()

    implicitHeight: 66
    radius: 14
    opacity: habilitada ? 1 : 0.45
    color: selecionada ? Tema.comAlfa(cor, 0.16)
                       : (area.containsMouse ? Tema.comAlfa(Tema.texto, 0.05) : "transparent")
    border.width: selecionada ? 2 : 1
    border.color: selecionada ? cor : Tema.borda

    Behavior on color { ColorAnimation { duration: Tema.rapida } }
    Behavior on border.color { ColorAnimation { duration: Tema.rapida } }

    Column {
        anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 14 }
        spacing: 3

        Row {
            spacing: 8
            Text {
                text: opcao.titulo
                color: Tema.texto
                font.family: Tema.fonte
                font.pixelSize: 15
                font.weight: Font.DemiBold
            }
            Rectangle {
                visible: opcao.selo !== ""
                anchors.verticalCenter: parent.verticalCenter
                width: textoSelo.implicitWidth + 12
                height: 18
                radius: 9
                color: Tema.comAlfa(opcao.cor, 0.25)
                Text {
                    id: textoSelo
                    anchors.centerIn: parent
                    text: opcao.selo
                    color: Qt.lighter(opcao.cor, 1.4)
                    font.family: Tema.fonte
                    font.pixelSize: 10
                    font.weight: Font.Bold
                }
            }
        }
        Text {
            visible: opcao.subtitulo !== ""
            width: parent.width
            text: opcao.subtitulo
            color: Tema.textoSuave
            font.family: Tema.fonte
            font.pixelSize: 12
            elide: Text.ElideRight
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        enabled: opcao.habilitada
        cursorShape: Qt.PointingHandCursor
        onClicked: opcao.clicada()
    }
}
