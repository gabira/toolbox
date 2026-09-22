import QtQuick
import QtQuick.Effects

// Brilho neon ao redor de um item. Uso: layer.enabled: true; layer.effect: Brilho { cor: ... }
MultiEffect {
    property color cor: "white"
    property real intensidade: 0.8

    shadowEnabled: true
    shadowColor: cor
    shadowOpacity: intensidade
    shadowBlur: 1.0
    shadowHorizontalOffset: 0
    shadowVerticalOffset: 0
    blurMax: 40
    autoPaddingEnabled: true
}
