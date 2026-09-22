import QtQuick
import QtQuick.Shapes
import QtQuick.Dialogs
import "../tema"
import "../componentes"

// Cena principal: hub central, bolhas dos apps em órbita e o app aberto.
//
// Estados: "trocando" (bolhas animando), "hub" (interativo), "abrindo", "app", "fechando".
Item {
    id: hub

    // --- geometria ---
    readonly property real base: Math.min(width, height)
    readonly property real centroX: width / 2
    readonly property real centroY: height / 2
    readonly property real diametroHub: base * 0.4
    readonly property real raioOrbita: base * 0.365
    readonly property real diametroBolha: Math.min(base * 0.175,
        2 * Math.PI * raioOrbita / Math.max(modelo.length, 1) * 0.8)
    readonly property real tamanhoCompacto: 56
    readonly property real margemCompacto: 16

    // --- estado ---
    property var modelo: []             // apps exibidos agora
    property real progresso: 0          // 0 = bolhas dentro do hub, 1 = em órbita
    property string estado: "trocando"
    property int indiceAberto: -1
    property bool trocaPendente: false
    property bool compacto: false
    property real k: compacto ? 1 : 0   // 0 = hub no centro, 1 = ícone no canto
    property bool analisando: false     // animação "Analisando arquivo" no círculo
    property var aposExpandir: null
    property var aposRecolher: null
    property var aposAnalise: null

    Behavior on k { NumberAnimation { duration: 620; easing.type: Easing.InOutCubic } }

    // --- tempos das bolhas: cada uma sai um pouco depois da anterior ---
    readonly property int duracaoBolha: 560
    readonly property int escalonamento: 75
    readonly property real duracaoTotal: duracaoBolha + escalonamento * Math.max(modelo.length - 1, 0)

    focus: true
    Keys.onEscapePressed: fecharApp()

    function lerp(a, b, t) { return a + (b - a) * t }

    function angulo(i) {
        return 2 * Math.PI * i / Math.max(modelo.length, 1) - Math.PI / 2
    }

    function posicaoBolha(i) {
        const a = angulo(i)
        return Qt.point(centroX + raioOrbita * Math.cos(a), centroY + raioOrbita * Math.sin(a))
    }

    // Progresso individual (0..1) da bolha i a partir do progresso global.
    function tLocal(i) {
        return Math.max(0, Math.min(1, (progresso * duracaoTotal - i * escalonamento) / duracaoBolha))
    }

    // Easing "out back": passa um pouco do ponto e volta, dando o efeito de mola.
    function suavizar(t) {
        const c1 = 1.4, c3 = c1 + 1
        return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2)
    }

    function expandir(depois) {
        animRecolher.stop()
        aposExpandir = depois || null
        animExpandir.duration = Math.max(1, duracaoTotal * (1 - progresso))
        animExpandir.start()
    }

    function recolher(depois) {
        animExpandir.stop()
        aposRecolher = depois || null
        animRecolher.duration = Math.max(1, duracaoTotal * 0.6 * progresso)
        animRecolher.start()
    }

    function executarAposAnimacao(nome) {
        const funcao = hub[nome]
        hub[nome] = null
        if (funcao)
            funcao()
    }

    function aoFicarOcioso() {
        estado = "hub"
        if (trocaPendente)
            atualizarApps()
    }

    // Arquivo mudou: bolhas voltam para dentro, a toolbox mostra a análise do
    // arquivo e só as compatíveis saem de novo.
    function atualizarApps() {
        if (estado !== "hub") {
            trocaPendente = true
            return
        }
        trocaPendente = false
        estado = "trocando"

        const comAnalise = nucleo.arquivo !== ""
        let recolhido = false
        let analisado = !comAnalise
        function seguir() {
            if (!recolhido || !analisado)
                return
            analisando = false
            modelo = nucleo.appsVisiveis
            expandir(aoFicarOcioso)
        }

        analisando = comAnalise
        if (comAnalise) {
            aposAnalise = function () { analisado = true; seguir() }
            timerAnalise.restart()
        }
        recolher(function () { recolhido = true; seguir() })
    }

    // Tempo mínimo da animação "Analisando arquivo" (a detecção em si é instantânea).
    Timer {
        id: timerAnalise
        interval: 1100
        onTriggered: hub.executarAposAnimacao("aposAnalise")
    }

    function abrirApp(i) {
        if (estado !== "hub")
            return
        estado = "abrindo"
        indiceAberto = i
        const p = posicaoBolha(i)
        painel.abrir(modelo[i], p.x, p.y, diametroBolha)
        compacto = true
        recolher(null)
    }

    function fecharApp() {
        if (estado !== "app")
            return
        estado = "fechando"
        compacto = false
        const p = posicaoBolha(indiceAberto)
        painel.fechar(p.x, p.y, function () {
            expandir(function () {
                indiceAberto = -1
                aoFicarOcioso()
            })
        })
    }

    NumberAnimation {
        id: animExpandir
        target: hub
        property: "progresso"
        to: 1
        onFinished: hub.executarAposAnimacao("aposExpandir")
    }

    NumberAnimation {
        id: animRecolher
        target: hub
        property: "progresso"
        to: 0
        easing.type: Easing.InQuad
        onFinished: hub.executarAposAnimacao("aposRecolher")
    }

    Connections {
        target: nucleo
        function onArquivoAlterado() { hub.atualizarApps() }
    }

    // Abertura: as bolhas saem do hub logo depois que a janela aparece.
    Timer {
        interval: 180
        running: true
        onTriggered: {
            hub.modelo = nucleo.appsVisiveis
            hub.expandir(hub.aoFicarOcioso)
        }
    }

    // --- fundo: brilho radial atrás do hub ---
    Shape {
        anchors.fill: parent
        opacity: 1 - hub.k * 0.7
        ShapePath {
            strokeWidth: -1
            fillGradient: RadialGradient {
                centerX: hub.centroX; centerY: hub.centroY
                focalX: hub.centroX; focalY: hub.centroY
                centerRadius: hub.base * 0.62
                focalRadius: 0
                GradientStop { position: 0; color: Tema.comAlfa(Tema.destaque, 0.17) }
                GradientStop { position: 0.55; color: Tema.comAlfa("#7C3AED", 0.05) }
                GradientStop { position: 1; color: "transparent" }
            }
            startX: 0; startY: 0
            PathLine { x: hub.width; y: 0 }
            PathLine { x: hub.width; y: hub.height }
            PathLine { x: 0; y: hub.height }
            PathLine { x: 0; y: 0 }
        }
    }

    // --- bolhas em órbita ---
    Repeater {
        model: hub.modelo

        delegate: Item {
            id: item

            required property var modelData
            required property int index

            // A bolha aberta fica parada no lugar (coberta pelo painel).
            readonly property bool fixa: index === hub.indiceAberto
            readonly property real t: fixa ? 1 : hub.tLocal(index)
            readonly property real e: fixa ? 1 : hub.suavizar(t)
            readonly property real a: hub.angulo(index)
            readonly property real distancia: hub.raioOrbita * e
            readonly property real escala: 0.3 + 0.7 * e

            anchors.fill: parent
            visible: t > 0

            Conector {
                cor: item.modelData.cor
                angulo: item.a
                origemX: hub.centroX
                origemY: hub.centroY
                inicio: hub.diametroHub / 2 + 6
                fim: item.distancia - hub.diametroBolha * item.escala / 2 - 6
                opacity: Math.min(1, item.t * 2)
            }

            BolhaApp {
                app: item.modelData
                width: hub.diametroBolha
                height: width
                x: hub.centroX + item.distancia * Math.cos(item.a) - width / 2
                y: hub.centroY + item.distancia * Math.sin(item.a) - height / 2
                scale: item.escala
                opacity: Math.min(1, item.t * 2.2)
                interativa: hub.estado === "hub"
                onClicada: hub.abrirApp(item.index)
            }
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 22
        opacity: 1 - hub.k
        visible: opacity > 0
        color: Tema.textoSuave
        font.family: Tema.fonte
        font.pixelSize: 13
        text: {
            if (hub.analisando)
                return "Analisando o arquivo para encontrar os apps compatíveis…"
            if (nucleo.totalApps === 0)
                return "Nenhum app instalado ainda."
            if (nucleo.arquivo === "")
                return "Arraste um arquivo para a TOOLBOX ou clique no centro para escolher."
            const n = nucleo.totalCompativeis
            if (n === 0)
                return "Nenhum app disponível para este tipo de arquivo."
            return n === 1 ? "1 app disponível para este arquivo." : n + " apps disponíveis para este arquivo."
        }
    }

    Text {
        anchors { right: parent.right; bottom: parent.bottom; margins: 14 }
        opacity: 1 - hub.k
        visible: opacity > 0
        text: "v" + nucleo.versao
        color: Tema.textoApagado
        font.family: Tema.fonte
        font.pixelSize: 11
    }

    PainelApp {
        id: painel
        anchors.fill: parent
        onAberto: hub.estado = "app"
    }

    CirculoToolbox {
        readonly property real diametro: hub.lerp(hub.diametroHub, hub.tamanhoCompacto, hub.k)
        readonly property real centro: hub.margemCompacto + hub.tamanhoCompacto / 2

        k: hub.k
        width: diametro
        height: diametro
        x: hub.lerp(hub.centroX, centro, hub.k) - diametro / 2
        y: hub.lerp(hub.centroY, centro, hub.k) - diametro / 2
        destacado: soltura.containsDrag
        analisando: hub.analisando
        nomeArquivo: nucleo.nomeArquivo
        resumo: nucleo.resumoArquivo
        onEscolherArquivo: dialogoArquivo.open()
        onLimparArquivo: nucleo.limparArquivo()
        onVoltar: hub.fecharApp()
    }

    DropArea {
        id: soltura
        anchors.fill: parent
        onEntered: (arrasto) => { arrasto.accepted = arrasto.hasUrls }
        onDropped: (soltado) => {
            if (soltado.hasUrls) {
                nucleo.definirArquivo(soltado.urls[0].toString())
                soltado.acceptProposedAction()
            }
        }
    }

    FileDialog {
        id: dialogoArquivo
        title: "Escolha um arquivo para a TOOLBOX"
        onAccepted: nucleo.definirArquivo(selectedFile.toString())
    }
}
