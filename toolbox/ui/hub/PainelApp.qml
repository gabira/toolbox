import QtQuick
import "../tema"
import "../componentes"

// Tela do app aberto. Surge como um círculo que cresce a partir da bolha clicada
// até cobrir a janela, e encolhe de volta para a bolha ao fechar.
Item {
    id: painel

    property var app: ({})
    property real origemX: 0
    property real origemY: 0
    property real diametroInicial: 100
    property real revelacao: 0          // 0 = do tamanho da bolha, 1 = janela toda
    property bool revelado: false
    property var aoFechar: null
    signal aberto()

    readonly property color cor: app.cor || Tema.destaque
    readonly property color corFundo: Tema.misturar(Tema.fundo, cor, 0.06)
    readonly property real diametroFinal: 2 * Math.sqrt(
        Math.pow(Math.max(origemX, width - origemX), 2) +
        Math.pow(Math.max(origemY, height - origemY), 2)) + 8
    // A cor da bolha vira a cor de fundo do app logo no começo da expansão.
    readonly property real mistura: Math.min(1, revelacao * 1.8)

    visible: revelacao > 0

    function abrir(dadosApp, x, y, diametro) {
        app = dadosApp
        origemX = x
        origemY = y
        diametroInicial = diametro
        revelado = false
        conteudo.opacity = 0
        carregador.setSource(dadosApp.tela, { controlador: nucleo.controlador(dadosApp.id) })
        animAbrir.start()
    }

    function fechar(x, y, depois) {
        origemX = x
        origemY = y
        aoFechar = depois
        animFechar.start()
    }

    function mostrarConteudo() {
        if (revelado && carregador.status !== Loader.Loading)
            animConteudo.start()
    }

    Rectangle {
        readonly property real d: painel.diametroInicial + (painel.diametroFinal - painel.diametroInicial) * painel.revelacao
        width: d
        height: d
        radius: d / 2
        x: painel.origemX - d / 2
        y: painel.origemY - d / 2
        gradient: Gradient {
            GradientStop { position: 0; color: Tema.misturar(Tema.misturar(Tema.fundo, painel.cor, 0.55), painel.corFundo, painel.mistura) }
            GradientStop { position: 1; color: Tema.misturar(Tema.misturar(Tema.fundo, painel.cor, 0.2), painel.corFundo, painel.mistura) }
        }
        border.width: 3 * (1 - painel.mistura)
        border.color: Qt.lighter(painel.cor, 1.2)

        // Imitação do conteúdo da bolha, que some nos primeiros instantes
        Column {
            anchors.centerIn: parent
            spacing: painel.diametroInicial * 0.04
            opacity: Math.max(0, 1 - painel.revelacao * 6)
            visible: opacity > 0

            Icone {
                anchors.horizontalCenter: parent.horizontalCenter
                fonte: painel.app.icone || ""
                resolucao: 96
                width: painel.diametroInicial * 0.3
                height: width
            }
            Text {
                width: painel.diametroInicial * 0.78
                horizontalAlignment: Text.AlignHCenter
                text: painel.app.nome || ""
                color: Tema.texto
                wrapMode: Text.WordWrap
                font.family: Tema.fonte
                font.pixelSize: Math.max(1, painel.diametroInicial * 0.1)
                font.weight: Font.Bold
            }
        }
    }

    // Brilho suave da cor do app no topo
    Rectangle {
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: parent.height * 0.5
        opacity: conteudo.opacity
        gradient: Gradient {
            GradientStop { position: 0; color: Tema.comAlfa(painel.cor, 0.12) }
            GradientStop { position: 1; color: "transparent" }
        }
    }

    Item {
        id: conteudo
        anchors.fill: parent
        opacity: 0
        visible: opacity > 0

        // Cabeçalho ao lado do ícone compacto da toolbox (canto superior esquerdo)
        Column {
            x: 90
            y: 20
            spacing: 2
            Text {
                text: painel.app.nome || ""
                color: Tema.texto
                font.family: Tema.fonte
                font.pixelSize: 24
                font.weight: Font.Bold
            }
            Text {
                text: painel.app.descricao || ""
                color: Tema.textoSuave
                font.family: Tema.fonte
                font.pixelSize: 13
            }
        }

        Loader {
            id: carregador
            asynchronous: true
            anchors { fill: parent; topMargin: 96 }
            transform: Translate { y: (1 - conteudo.opacity) * 18 }
            onStatusChanged: painel.mostrarConteudo()
        }
    }

    NumberAnimation {
        id: animAbrir
        target: painel
        property: "revelacao"
        from: 0.001
        to: 1
        duration: 640
        easing.type: Easing.InOutCubic
        onFinished: {
            painel.revelado = true
            painel.aberto()
            painel.mostrarConteudo()
        }
    }

    NumberAnimation {
        id: animConteudo
        target: conteudo
        property: "opacity"
        to: 1
        duration: 280
        easing.type: Easing.OutCubic
    }

    SequentialAnimation {
        id: animFechar
        ScriptAction { script: animConteudo.stop() }
        NumberAnimation { target: conteudo; property: "opacity"; to: 0; duration: 150 }
        NumberAnimation {
            target: painel
            property: "revelacao"
            to: 0
            duration: 560
            easing.type: Easing.InOutCubic
        }
        ScriptAction {
            script: {
                carregador.source = ""
                painel.revelado = false
                const depois = painel.aoFechar
                painel.aoFechar = null
                if (depois)
                    depois()
            }
        }
    }
}
