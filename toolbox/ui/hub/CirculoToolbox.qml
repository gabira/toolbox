import QtQuick
import QtQuick.Shapes
import "../tema"
import "../componentes"

// Círculo central. `k` vai de 0 (hub no centro) a 1 (ícone compacto no canto).
Item {
    id: circulo

    property real k: 0
    property bool destacado: false      // arquivo sendo arrastado por cima
    property bool analisando: false     // detectando o tipo da entrada
    property string tipoEntrada: ""     // "", "arquivo" ou "link"
    property string nomeEntrada: ""
    property string resumo: ""
    readonly property bool editando: campo.activeFocus
    readonly property bool temEntrada: tipoEntrada !== ""
    signal escolherArquivo()
    signal enviarTexto(string texto)
    signal limpar()
    signal voltar()

    readonly property real d: width
    readonly property real opacidadeConteudo: Math.max(0, 1 - k * 3)
    readonly property bool compacto: k > 0.99

    function lerp(a, b, t) { return a + (b - a) * t }

    // Mensagem curta em vermelho abaixo da entrada (ex.: link não reconhecido)
    property string erro: ""
    function mostrarErro(mensagem) {
        erro = mensagem
        timerErro.restart()
    }
    Timer { id: timerErro; interval: 3200; onTriggered: circulo.erro = "" }

    function enviarCampo() {
        const texto = campo.text.trim()
        timerEnvio.stop()
        if (texto === "")
            return
        campo.text = ""
        campo.focus = false
        circulo.enviarTexto(texto)
    }

    // Colou/digitou algo com cara de link: envia sozinho, sem precisar de Enter.
    Timer { id: timerEnvio; interval: 450; onTriggered: circulo.enviarCampo() }

    scale: compacto && areaCirculo.containsMouse ? 1.1 : (destacado ? 1.04 : 1)
    Behavior on scale { NumberAnimation { duration: 220; easing.type: Easing.OutBack } }

    // Anel tracejado neon ao redor
    Shape {
        id: anel
        readonly property real espessura: Math.max(2, circulo.d * 0.012)
        readonly property real r: circulo.d / 2 + Math.max(5, circulo.d * 0.04)
        readonly property int tracos: 16
        // comprimento de um traço + intervalo, em unidades da espessura (padrão do DashLine)
        readonly property real passo: 2 * Math.PI * r / tracos / espessura

        anchors.centerIn: parent
        width: 2 * (r + espessura)
        height: width
        layer.enabled: true
        layer.samples: 4
        layer.effect: Brilho { cor: Tema.ciano; intensidade: circulo.destacado ? 1 : 0.8 }

        ShapePath {
            strokeColor: circulo.destacado || circulo.analisando ? "#A5F3FC" : Tema.ciano
            strokeWidth: anel.espessura
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            strokeStyle: ShapePath.DashLine
            dashPattern: [Math.max(0.1, anel.passo * 0.64 - 1), anel.passo * 0.36 + 1]

            PathAngleArc {
                centerX: anel.width / 2
                centerY: anel.height / 2
                radiusX: anel.r
                radiusY: anel.r
                startAngle: -90
                sweepAngle: 360
            }
        }

        // Gira só ao arrastar ou analisar um arquivo (sem animação contínua em repouso).
        FrameAnimation {
            running: circulo.destacado || circulo.analisando
            onTriggered: anel.rotation = (anel.rotation + frameTime * (circulo.analisando ? 150 : 45)) % 360
        }
    }

    // Arco de varredura que gira no sentido contrário durante a análise
    Shape {
        id: varredura
        anchors.fill: anel
        opacity: circulo.analisando ? 1 : 0
        visible: opacity > 0
        layer.enabled: visible
        layer.samples: 4
        layer.effect: Brilho { cor: "#A5F3FC"; intensidade: 1 }

        Behavior on opacity { NumberAnimation { duration: 260 } }

        ShapePath {
            strokeColor: "#E0FBFF"
            strokeWidth: anel.espessura * 1.6
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            PathAngleArc {
                centerX: varredura.width / 2
                centerY: varredura.height / 2
                radiusX: anel.r
                radiusY: anel.r
                startAngle: 0
                sweepAngle: 70
            }
        }

        FrameAnimation {
            running: varredura.visible
            onTriggered: varredura.rotation = (varredura.rotation - frameTime * 260) % 360
        }
    }

    // Corpo
    Rectangle {
        anchors.fill: parent
        radius: width / 2
        gradient: Gradient {
            GradientStop { position: 0; color: "#15275C" }
            GradientStop { position: 1; color: "#070E27" }
        }
        border.width: Math.max(1.5, circulo.d * 0.008)
        border.color: circulo.destacado ? Tema.ciano : Tema.destaque
        layer.enabled: true
        layer.effect: Brilho { cor: Tema.destaque; intensidade: circulo.destacado ? 1 : 0.7 }
    }

    MouseArea {
        id: areaCirculo
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: (evento) => {
            const dx = evento.x - width / 2, dy = evento.y - height / 2
            if (dx * dx + dy * dy > width * width / 4)
                return
            if (circulo.compacto)
                circulo.voltar()
            else if (circulo.k === 0 && !circulo.analisando)
                circulo.escolherArquivo()
        }
    }

    // Reticências animadas de "Analisando arquivo..."
    property int pontos: 0
    Timer {
        interval: 320
        repeat: true
        running: circulo.analisando
        onTriggered: circulo.pontos = (circulo.pontos + 1) % 4
        onRunningChanged: circulo.pontos = 0
    }

    // Símbolo "T" do logo: só aparece no modo compacto (ícone do canto com o app aberto)
    Image {
        readonly property real tamanho: circulo.d * 0.68
        source: Tema.imagem("logo_simbolo")
        sourceSize: Qt.size(128, 128)
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        width: tamanho
        height: tamanho
        x: (circulo.d - tamanho) / 2
        y: (circulo.d - tamanho) / 2
        opacity: Math.max(0, circulo.k * 3 - 2)
        visible: opacity > 0
    }

    // Palavra "TOOLBOX" do logo (pulsa durante a análise)
    Image {
        anchors.horizontalCenter: parent.horizontalCenter
        y: circulo.d * 0.29
        width: circulo.d * 0.62
        height: width * 229 / 799
        source: Tema.imagem("logo_texto")
        sourceSize: Qt.size(600, 172)
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        opacity: circulo.opacidadeConteudo
        visible: opacity > 0

        SequentialAnimation on scale {
            running: circulo.analisando
            loops: Animation.Infinite
            alwaysRunToEnd: true
            NumberAnimation { to: 1.06; duration: 420; easing.type: Easing.OutQuad }
            NumberAnimation { to: 1; duration: 420; easing.type: Easing.InQuad }
        }
    }

    // Entrada híbrida compartilhada: arquivo (ícone de pasta / arrastar) ou link (colar/digitar)
    Rectangle {
        id: entrada
        width: circulo.d * 0.76
        height: circulo.d * 0.15
        anchors.horizontalCenter: parent.horizontalCenter
        y: circulo.d * 0.51
        radius: height / 2
        opacity: circulo.opacidadeConteudo
        visible: opacity > 0
        color: circulo.editando ? "#0E1B45" : (areaCirculo.containsMouse ? "#12214F" : "#0A1334")
        border.width: circulo.editando ? 2 : 1.5
        border.color: circulo.erro !== "" ? Tema.erro
                      : (circulo.editando || circulo.temEntrada ? Tema.ciano : Tema.comAlfa(Tema.destaqueClaro, 0.45))

        Behavior on color { ColorAnimation { duration: Tema.rapida } }
        Behavior on border.color { ColorAnimation { duration: Tema.rapida } }

        // Tremida quando o texto não é reconhecido
        transform: Translate { id: deslocamento }
        SequentialAnimation {
            id: tremida
            NumberAnimation { target: deslocamento; property: "x"; to: -8; duration: 50 }
            NumberAnimation { target: deslocamento; property: "x"; to: 8; duration: 70 }
            NumberAnimation { target: deslocamento; property: "x"; to: -5; duration: 60 }
            NumberAnimation { target: deslocamento; property: "x"; to: 0; duration: 50 }
        }
        Connections {
            target: circulo
            function onErroChanged() { if (circulo.erro !== "") tremida.restart() }
        }

        // Ícone da esquerda: abre o seletor de arquivos
        Item {
            id: iconeEntrada
            width: entrada.height * 0.9
            height: entrada.height
            x: entrada.height * 0.14

            Icone {
                anchors.centerIn: parent
                nome: circulo.tipoEntrada === "link" && !circulo.editando ? "link" : "pasta"
                resolucao: 48
                width: entrada.height * 0.42
                height: width
                opacity: areaPasta.containsMouse ? 1 : 0.85
            }
            MouseArea {
                id: areaPasta
                anchors.fill: parent
                hoverEnabled: true
                enabled: circulo.k === 0 && !circulo.analisando
                cursorShape: Qt.PointingHandCursor
                onClicked: circulo.escolherArquivo()
            }
        }

        TextInput {
            id: campo
            anchors {
                left: iconeEntrada.right; leftMargin: entrada.height * 0.05
                right: botaoAcao.left; rightMargin: entrada.height * 0.2
                verticalCenter: parent.verticalCenter
            }
            enabled: circulo.k === 0 && !circulo.analisando
            clip: true
            selectByMouse: true
            color: Tema.texto
            selectionColor: Tema.comAlfa(Tema.ciano, 0.5)
            font.family: Tema.fonte
            font.pixelSize: Math.max(1, entrada.height * 0.3)
            font.weight: Font.DemiBold
            onAccepted: circulo.enviarCampo()
            onTextEdited: {
                if (/https?:\/\/|youtu\.?be/i.test(text))
                    timerEnvio.restart()
            }
            Keys.onEscapePressed: {
                text = ""
                focus = false
            }

            // Texto de apoio / nome da entrada atual (some quando o usuário digita)
            Text {
                anchors.fill: parent
                verticalAlignment: Text.AlignVCenter
                visible: campo.text === ""
                elide: Text.ElideMiddle
                font: campo.font
                text: {
                    if (circulo.analisando)
                        return (circulo.tipoEntrada === "link" ? "Analisando link" : "Analisando arquivo")
                               + ".".repeat(circulo.pontos)
                    if (circulo.editando)
                        return "Cole um link do YouTube…"
                    return circulo.temEntrada ? circulo.nomeEntrada : "Arquivo ou link"
                }
                color: circulo.analisando ? "#A5F3FC"
                       : (circulo.temEntrada && !circulo.editando ? Tema.texto : Tema.textoSuave)
            }
        }

        Rectangle {
            id: botaoAcao
            width: entrada.height * 0.74
            height: width
            radius: width / 2
            anchors.right: parent.right
            anchors.rightMargin: entrada.height * 0.13
            anchors.verticalCenter: parent.verticalCenter
            color: areaAcao.containsMouse ? Tema.destaqueClaro : Tema.destaque
            layer.enabled: true
            layer.effect: Brilho { cor: Tema.destaque; intensidade: 0.8 }

            Behavior on color { ColorAnimation { duration: Tema.rapida } }

            // Com texto digitado: enviar. Com entrada: limpar. Vazio: escolher arquivo.
            readonly property string acao: campo.text !== "" ? "enviar" : (circulo.temEntrada ? "limpar" : "escolher")

            Icone {
                anchors.centerIn: parent
                nome: botaoAcao.acao === "limpar" ? "fechar" : "seta"
                resolucao: 40
                width: parent.width * 0.5
                height: width
            }

            MouseArea {
                id: areaAcao
                anchors.fill: parent
                hoverEnabled: true
                enabled: circulo.k === 0 && !circulo.analisando
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (botaoAcao.acao === "enviar") circulo.enviarCampo()
                    else if (botaoAcao.acao === "limpar") circulo.limpar()
                    else circulo.escolherArquivo()
                }
            }
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: entrada.y + entrada.height + circulo.d * 0.035
        width: circulo.d * 0.72
        horizontalAlignment: Text.AlignHCenter
        text: {
            if (circulo.erro !== "")
                return circulo.erro
            if (circulo.analisando)
                return circulo.nomeEntrada
            return circulo.resumo !== "" ? circulo.resumo : "arraste um arquivo ou cole um link"
        }
        color: circulo.erro !== "" ? Tema.erro : Tema.textoSuave
        opacity: circulo.opacidadeConteudo
        visible: opacity > 0
        elide: Text.ElideRight
        font.family: Tema.fonte
        font.pixelSize: Math.max(1, circulo.d * 0.042)
    }
}
