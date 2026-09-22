import QtQuick
import "../tema"

// Ícone SVG. Use `nome` para os ícones da UI (ui/icones) ou `fonte` para um caminho/URL.
Image {
    property string nome: ""
    property url fonte: ""
    // Resolução de rasterização fixa: redimensionar durante animações não re-renderiza o SVG.
    property int resolucao: 64

    source: fonte.toString() !== "" ? fonte : (nome !== "" ? Tema.icone(nome) : "")
    sourceSize: Qt.size(resolucao, resolucao)
    fillMode: Image.PreserveAspectFit
    smooth: true
    mipmap: true
}
