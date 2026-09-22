import QtQuick
import QtQuick.Shapes
import "../tema"
import "../componentes"

// Círculo central. `k` vai de 0 (hub no centro) a 1 (ícone compacto no canto).
Item {
    id: circulo

    property real k: 0
    property bool destacado: false      // arquivo sendo arrastado por cima
    property string nomeArquivo: ""
    property string resumo: ""
    signal escolherArquivo()
    signal limparArquivo()
    signal voltar()

    readonly property real d: width
    readonly property real opacidadeConteudo: Math.max(0, 1 - k * 3)
    readonly property bool compacto: k > 0.99

    function lerp(a, b, t) { return a + (b - a) * t }

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
            strokeColor: circulo.destacado ? "#A5F3FC" : Tema.ciano
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

        // Gira só enquanto um arquivo é arrastado (sem animação contínua em repouso).
        FrameAnimation {
            running: circulo.destacado
            onTriggered: anel.rotation = (anel.rotation + frameTime * 45) % 360
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
            else if (circulo.k === 0)
                circulo.escolherArquivo()
        }
    }

    Icone {
        readonly property real tamanho: circulo.lerp(circulo.d * 0.2, circulo.d * 0.54, circulo.k)
        nome: "cubo"
        resolucao: 160
        width: tamanho
        height: tamanho
        x: (circulo.d - tamanho) / 2
        y: circulo.lerp(circulo.d * 0.15, (circulo.d - tamanho) / 2, circulo.k)
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: circulo.d * 0.39
        text: "TOOLBOX"
        color: Tema.texto
        opacity: circulo.opacidadeConteudo
        visible: opacity > 0
        font.family: Tema.fonte
        font.pixelSize: Math.max(1, circulo.d * 0.11)
        font.weight: Font.Black
        font.letterSpacing: circulo.d * 0.004
    }

    // Entrada de arquivo compartilhada
    Rectangle {
        id: entrada
        width: circulo.d * 0.76
        height: circulo.d * 0.15
        anchors.horizontalCenter: parent.horizontalCenter
        y: circulo.d * 0.585
        radius: height / 2
        opacity: circulo.opacidadeConteudo
        visible: opacity > 0
        color: areaCirculo.containsMouse ? "#12214F" : "#0A1334"
        border.width: 1.5
        border.color: circulo.nomeArquivo !== "" ? Tema.ciano : Tema.comAlfa(Tema.destaqueClaro, 0.45)

        Behavior on color { ColorAnimation { duration: Tema.rapida } }

        Icone {
            id: iconePasta
            nome: "pasta"
            resolucao: 48
            width: entrada.height * 0.42
            height: width
            x: entrada.height * 0.38
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            anchors {
                left: iconePasta.right; leftMargin: entrada.height * 0.25
                right: botaoAcao.left; rightMargin: entrada.height * 0.2
                verticalCenter: parent.verticalCenter
            }
            text: circulo.nomeArquivo !== "" ? circulo.nomeArquivo : "Selecionar arquivo"
            elide: Text.ElideMiddle
            color: circulo.nomeArquivo !== "" ? Tema.texto : Tema.textoSuave
            font.family: Tema.fonte
            font.pixelSize: Math.max(1, entrada.height * 0.3)
            font.weight: Font.DemiBold
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

            Icone {
                anchors.centerIn: parent
                nome: circulo.nomeArquivo !== "" ? "fechar" : "seta"
                resolucao: 40
                width: parent.width * 0.5
                height: width
            }

            MouseArea {
                id: areaAcao
                anchors.fill: parent
                hoverEnabled: true
                enabled: circulo.k === 0
                cursorShape: Qt.PointingHandCursor
                onClicked: circulo.nomeArquivo !== "" ? circulo.limparArquivo() : circulo.escolherArquivo()
            }
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: entrada.y + entrada.height + circulo.d * 0.035
        width: circulo.d * 0.7
        horizontalAlignment: Text.AlignHCenter
        text: circulo.resumo !== "" ? circulo.resumo : "ou arraste para cá"
        color: Tema.textoSuave
        opacity: circulo.opacidadeConteudo
        visible: opacity > 0
        elide: Text.ElideRight
        font.family: Tema.fonte
        font.pixelSize: Math.max(1, circulo.d * 0.042)
    }
}
