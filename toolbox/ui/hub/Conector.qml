import QtQuick
import "../tema"

// Linha luminosa entre a borda do hub e a borda de uma bolha.
Item {
    id: conector

    property color cor: Tema.destaque
    property real angulo: 0          // radianos
    property real origemX: 0         // centro do hub
    property real origemY: 0
    property real inicio: 0          // distância do centro onde a linha começa
    property real fim: 0             // distância do centro onde a linha termina

    readonly property real comprimento: Math.max(0, fim - inicio)
    readonly property real cosA: Math.cos(angulo)
    readonly property real senA: Math.sin(angulo)
    readonly property color corClara: Qt.lighter(cor, 1.35)

    visible: comprimento > 2

    component Linha: Rectangle {
        x: conector.origemX + conector.inicio * conector.cosA
        y: conector.origemY + conector.inicio * conector.senA - height / 2
        width: conector.comprimento
        radius: height / 2
        transformOrigin: Item.Left
        rotation: conector.angulo * 180 / Math.PI
    }

    component Ponto: Item {
        property real distancia: 0
        x: conector.origemX + distancia * conector.cosA
        y: conector.origemY + distancia * conector.senA

        Rectangle {
            width: 22; height: 22; radius: 11
            x: -11; y: -11
            color: Tema.comAlfa(conector.cor, 0.28)
        }
        Rectangle {
            width: 11; height: 11; radius: 5.5
            x: -5.5; y: -5.5
            color: conector.corClara
            border.width: 1.5
            border.color: Tema.comAlfa("white", 0.85)
        }
    }

    Linha { height: 9; color: Tema.comAlfa(conector.cor, 0.2) }
    Linha { height: 3; color: conector.corClara }
    Ponto { distancia: conector.inicio }
    Ponto { distancia: conector.fim }
}
