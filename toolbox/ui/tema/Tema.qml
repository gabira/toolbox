pragma Singleton
import QtQuick

// Cores, fontes e tempos compartilhados por toda a interface.
QtObject {
    readonly property color fundo: "#060A17"
    readonly property color fundoElevado: "#0B1128"
    readonly property color superficie: "#0F1733"
    readonly property color borda: "#23305C"
    readonly property color texto: "#EEF2FF"
    readonly property color textoSuave: "#98A3CC"
    readonly property color textoApagado: "#5F6A94"

    readonly property color destaque: "#3B82F6"
    readonly property color destaqueClaro: "#7CB7FF"
    readonly property color ciano: "#38BDF8"
    readonly property color sucesso: "#34D399"
    readonly property color erro: "#FB7185"

    readonly property string fonte: "Segoe UI"

    readonly property int rapida: 160
    readonly property int media: 320
    readonly property int lenta: 600

    function misturar(a, b, t) {
        return Qt.rgba(a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t,
                       a.b + (b.b - a.b) * t, a.a + (b.a - a.a) * t)
    }

    function comAlfa(c, alfa) {
        return Qt.rgba(c.r, c.g, c.b, alfa)
    }

    function icone(nome) {
        return Qt.resolvedUrl("../icones/" + nome + ".svg")
    }
}
