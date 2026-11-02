// Carta de jogador no estilo dos jogos de futebol: moldura nas cores do clube, a foto real do
// atleta (Wikimedia Commons, jogador confirmado) recortada em meio corpo e os números da
// temporada como atributos. Sem foto confirmada, a carta mostra a camisa do clube com as iniciais,
// sem inventar um rosto.
import { h } from "./ui.js";
import { escudo, foto, iniciais } from "./imagens.js";
import { textoSobre } from "./cores.js";

const SIGLAS = { Goleiro: "GOL", Zagueiro: "ZAG", Lateral: "LAT", "Meio-campo": "MEI", Atacante: "ATA" };
const SVG = "http://www.w3.org/2000/svg";

function camisa(clube, texto) {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", "0 0 120 120");
  svg.setAttribute("class", "carta-camisa");
  svg.setAttribute("aria-hidden", "true");
  const corpo = document.createElementNS(SVG, "path");
  corpo.setAttribute("d", "M38 14 L50 10 Q60 18 70 10 L82 14 L108 30 L98 52 L86 46 L86 112 L34 112 L34 46 L22 52 L12 30 Z");
  corpo.setAttribute("fill", clube.cor2);
  corpo.setAttribute("stroke", "rgba(0,0,0,.25)");
  corpo.setAttribute("stroke-width", "1.5");
  const gola = document.createElementNS(SVG, "path");
  gola.setAttribute("d", "M50 10 Q60 22 70 10");
  gola.setAttribute("fill", "none");
  gola.setAttribute("stroke", clube.cor1);
  gola.setAttribute("stroke-width", "4");
  const sigla = document.createElementNS(SVG, "text");
  sigla.setAttribute("x", "60");
  sigla.setAttribute("y", "76");
  sigla.setAttribute("text-anchor", "middle");
  sigla.setAttribute("font-size", "26");
  sigla.setAttribute("font-weight", "800");
  sigla.setAttribute("fill", textoSobre(clube.cor2));
  sigla.textContent = texto;
  svg.append(corpo, gola, sigla);
  return svg;
}

// atributos: [[sigla, valor]] (até 6). destaque: { valor, rotulo } no canto da carta.
export function cartaJogador(jogador, clube, { destaque, atributos = [], classe = "", link = null } = {}) {
  const texto = textoSobre(clube.cor1);
  const retrato = h("div", { class: "carta-retrato" }, camisa(clube, iniciais(jogador.nome)), foto(jogador, clube, "foto-carta"));
  const conteudo = [
    h("div", { class: "carta-cabeca" },
      h("div", { class: "carta-nota" }, h("strong", {}, destaque.valor), h("span", {}, destaque.rotulo)),
      h("div", { class: "carta-pos" }, SIGLAS[jogador.pos] || "—"),
      escudo(clube)),
    retrato,
    h("div", { class: "carta-nome" }, jogador.nome),
    atributos.length ? h("dl", { class: "carta-atributos" },
      atributos.map(([sigla, valor]) => h("div", {}, h("dt", {}, sigla), h("dd", {}, valor)))) : null,
  ];
  const atrs = {
    class: `carta ${jogador.selecao ? "carta-ouro" : ""} ${classe}`.trim(),
    style: { "--carta-c1": clube.cor1, "--carta-c2": clube.cor2, "--carta-texto": texto },
    "aria-label": `${jogador.nome}, ${clube.nome}`,
  };
  return link ? h("a", { ...atrs, href: link }, conteudo) : h("article", atrs, conteudo);
}
