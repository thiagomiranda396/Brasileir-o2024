// Utilitários de DOM. Todo texto vindo dos dados entra como nó de texto (nunca innerHTML).
import { escudo } from "./imagens.js";

export function h(tag, attrs = {}, ...filhos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") e.className = v;
    else if (k.startsWith("on") && typeof v === "function") e.addEventListener(k.slice(2), v);
    else if (k === "style" && typeof v === "object") {
      for (const [prop, valor] of Object.entries(v)) {
        if (prop.startsWith("--")) e.style.setProperty(prop, valor);  // variáveis CSS (cores do clube)
        else e.style[prop] = valor;
      }
    }
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const f of filhos.flat()) {
    if (f === null || f === undefined || f === false) continue;
    e.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return e;
}

export function clubeInline(clube, { link = true, classe = "" } = {}) {
  const conteudo = [escudo(clube, classe), h("span", {}, clube.nome)];
  return link
    ? h("a", { class: "clube-inline", href: `#/clubes/${clube.id}`, style: { color: "inherit", textDecoration: "none" } }, conteudo)
    : h("span", { class: "clube-inline" }, conteudo);
}

// Título da página: vai para a faixa verde do topo, sozinho. Os extras (busca, seletores) vão para
// a barra lateral de filtros. Devolve o subtítulo, que abre o conteúdo da página.
export function cabecalho(titulo, subtitulo, ...extras) {
  faixaTitulo({ titulo });
  if (extras.length) filtros(...extras);
  return subtitulo ? h("p", { class: "intro" }, subtitulo) : document.createComment("título na faixa do topo");
}

// Faixa do topo. Com `cores` (página de um clube), usa as cores do time no lugar do verde.
export function faixaTitulo({ titulo, simbolo = null, cores = null, rotulo = null }) {
  const faixa = document.getElementById("faixa-titulo");
  if (!faixa) return;
  faixa.classList.toggle("faixa-clube", Boolean(cores));
  if (cores) {
    faixa.style.setProperty("--faixa-fundo", cores.fundo);
    faixa.style.setProperty("--faixa-texto", cores.texto);
    faixa.style.setProperty("--faixa-listra", cores.listra);
  } else {
    for (const v of ["--faixa-fundo", "--faixa-texto", "--faixa-listra"]) faixa.style.removeProperty(v);
  }
  faixa.replaceChildren(h("div", { class: "faixa-interna" },
    simbolo,
    h("div", { class: "faixa-textos" },
      rotulo ? h("div", { class: "faixa-rotulo" }, rotulo) : null,
      h("h1", {}, titulo))));
}

// Filtros da página, na barra lateral. Cada item é um controle ou [rótulo, controle].
export function filtros(...itens) {
  const area = document.getElementById("filtros");
  if (!area) return;
  for (const item of itens.flat()) {
    if (!item) continue;
    if (Array.isArray(item)) {
      const [rotulo, controle] = item;
      area.append(h("label", { class: "filtro" }, h("span", { class: "filtro-rotulo" }, rotulo), controle));
    } else {
      area.append(h("div", { class: "filtro" }, item));
    }
  }
  area.closest(".painel-filtros")?.removeAttribute("hidden");
}

export function cartao(titulo, sub, ...conteudo) {
  return h("section", { class: "cartao" }, titulo ? h("h2", {}, titulo) : null,
    sub ? h("p", { class: "sub" }, sub) : null, ...conteudo);
}

export function kpi(rotulo, valor, detalhe = null) {
  return h("div", { class: "kpi" }, h("span", { class: "kpi-rotulo" }, rotulo),
    h("span", { class: "kpi-valor" }, valor), detalhe ? h("span", { class: "kpi-detalhe" }, detalhe) : null);
}

export function forma(resultados) {
  const nomes = { V: "Vitória", E: "Empate", D: "Derrota" };
  return h("span", { class: "forma", "aria-label": resultados.map((r) => nomes[r]).join(", ") },
    resultados.map((r) => h("b", { class: r, title: nomes[r] }, r)));
}

export const ZONAS = {
  "Campeão": "zona-campeao",
  "Libertadores (fase de grupos)": "zona-lib",
  "Libertadores (2ª fase)": "zona-lib2",
  "Sul-Americana": "zona-sula",
  "Rebaixado": "zona-rebaixado",
  "Sem vaga": "",
};

export function lerPreferencia(chave, padrao) {
  try { return JSON.parse(localStorage.getItem(chave)) ?? padrao; } catch { return padrao; }
}

export function gravarPreferencia(chave, valor) {
  try { localStorage.setItem(chave, JSON.stringify(valor)); } catch { /* sem armazenamento */ }
}

// Faixa de indicadores: cada um num cartão do mesmo tamanho (rótulo, valor, detalhe).
export function faixaKpis(itens, { colunas = 4 } = {}) {
  return h("div", { class: `faixa-kpis faixa-${colunas}` },
    itens.filter(Boolean).map(([rotulo, valor, detalhe]) => h("div", { class: "cartao" }, kpi(rotulo, valor, detalhe))));
}

// Bloco da página com título próprio, para separar os assuntos sem empilhar cartões soltos.
export function secao(titulo, sub, ...conteudo) {
  return h("section", { class: "secao" },
    h("div", { class: "secao-cabecalho" }, h("h2", {}, titulo), sub ? h("p", {}, sub) : null), ...conteudo);
}

// Monta o endereço de uma página: rota("clubes", "BOT") -> "#/clubes/BOT".
export const rota = (...partes) => `#/${partes.filter((p) => p !== undefined && p !== "").join("/")}`;

// Abas de uma página. Cada aba é um endereço, então o botão Voltar funciona.
// opcoes: [[id, nome, endereço]].
export function abasPagina(opcoes, atual) {
  return h("nav", { class: "abas-pagina", "aria-label": "Seções da página" },
    opcoes.map(([id, nome, href]) => h("a", { href, "aria-current": id === atual ? "page" : null }, nome)));
}

// Lista que mostra os primeiros itens e abre o resto sob demanda.
export function listaComMais(itens, desenhar, { inicial = 10, classe = "lista-rank", rotulo = "itens" } = {}) {
  const lista = h("ol", { class: classe });
  let mostrando = Math.min(inicial, itens.length);
  const botao = h("button", { class: "botao botao-discreto", type: "button" });
  const atualizar = () => {
    lista.replaceChildren(...itens.slice(0, mostrando).map(desenhar));
    botao.hidden = mostrando >= itens.length;
    botao.textContent = `Mostrar mais (${itens.length - mostrando} ${rotulo})`;
  };
  botao.addEventListener("click", () => { mostrando = Math.min(itens.length, mostrando + 15); atualizar(); });
  atualizar();
  return h("div", {}, lista, botao);
}
