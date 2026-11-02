// Cores dos clubes: contraste (WCAG) para escolher texto e séries legíveis em cada tema.

function rgb(hex) {
  const h = hex.replace("#", "");
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
}

function luminancia(hex) {
  const [r, g, b] = rgb(hex).map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contraste(a, b) {
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

const BRANCO = "#ffffff";
const PRETO = "#111111";

// Texto sobre uma cor de fundo: branco ou quase preto, o que tiver mais contraste.
export function textoSobre(fundo) {
  return contraste(fundo, BRANCO) >= contraste(fundo, PRETO) ? BRANCO : PRETO;
}

// Faixa do topo na página do clube: fundo na cor principal e listra na secundária.
export function coresFaixa(clube) {
  const texto = textoSobre(clube.cor1);
  const listra = contraste(clube.cor1, clube.cor2) >= 1.5 ? clube.cor2 : texto;
  return { fundo: clube.cor1, texto, listra };
}

function misturar(hex, alvo, t) {
  const a = rgb(hex), b = rgb(alvo);
  return `#${a.map((c, i) => Math.round(c + (b[i] - c) * t).toString(16).padStart(2, "0")).join("")}`;
}

function fundoAtual() {
  const valor = getComputedStyle(document.documentElement).getPropertyValue("--superficie").trim();
  return /^#[0-9a-f]{6}$/i.test(valor) ? valor : "#fcfcfb";
}

// Cor do clube para marcas de gráfico: a primeira das cores do clube com contraste 3:1 sobre o
// cartão; se nenhuma tiver (preto no tema escuro, amarelo no claro), clareia ou escurece a principal.
export function corSerieClube(clube) {
  const fundo = fundoAtual();
  for (const cor of [clube.cor1, clube.cor2]) if (contraste(cor, fundo) >= 3) return cor;
  const alvo = luminancia(fundo) > 0.5 ? PRETO : BRANCO;
  let cor = clube.cor1;
  for (let t = 0.15; t <= 1 && contraste(cor, fundo) < 3; t += 0.15) cor = misturar(clube.cor1, alvo, t);
  return cor;
}

// Cor de comparação ao lado da cor do clube: cinza neutro, ou laranja se o clube já for acinzentado.
export function corComparacao(corClube) {
  const [r, g, b] = rgb(corClube);
  return Math.max(r, g, b) - Math.min(r, g, b) < 48 ? "var(--serie-3)" : "var(--neutro-serie)";
}
