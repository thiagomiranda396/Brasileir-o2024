// Gráficos em SVG puro: colunas (uma série), colunas agrupadas (duas séries) e linhas de
// posição por rodada. Marcas finas, pontas arredondadas de 4px, grade recessiva, tooltip
// em todo gráfico e textos sempre com as cores de texto (nunca a cor da série).

const SVG = "http://www.w3.org/2000/svg";
const tooltipEl = () => document.querySelector(".tooltip");

export function el(tag, attrs = {}, pai = null) {
  const e = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (pai) pai.append(e);
  return e;
}

// --- Tooltip ----------------------------------------------------------------
// linhas: [{ valor, rotulo, cor? }]; tudo inserido com textContent.
export function mostrarTooltip(evento, titulo, linhas) {
  const tt = tooltipEl();
  tt.replaceChildren();
  if (titulo) {
    const t = document.createElement("div");
    t.className = "tt-titulo";
    t.textContent = titulo;
    tt.append(t);
  }
  for (const l of linhas) {
    const d = document.createElement("div");
    d.className = "tt-linha";
    if (l.cor) {
      const i = document.createElement("i");
      i.style.background = l.cor;
      d.append(i);
    }
    const s = document.createElement("strong");
    s.textContent = l.valor;
    d.append(s);
    if (l.rotulo) d.append(document.createTextNode(` ${l.rotulo}`));
    tt.append(d);
  }
  tt.hidden = false;
  posicionar(evento);
}

function posicionar(evento) {
  const tt = tooltipEl();
  let x, y;
  if (evento.clientX !== undefined && evento.type !== "focus") {
    x = evento.clientX; y = evento.clientY;
  } else {
    const r = evento.target.getBoundingClientRect();
    x = r.left + r.width / 2; y = r.top;
  }
  const larg = tt.offsetWidth, alt = tt.offsetHeight;
  let left = x + 14, top = y - alt - 10;
  if (left + larg > window.innerWidth - 8) left = x - larg - 14;
  if (top < 8) top = y + 16;
  tt.style.left = `${Math.max(8, left)}px`;
  tt.style.top = `${top}px`;
}

export function esconderTooltip() {
  tooltipEl().hidden = true;
}

// Re-renderiza quando o contêiner muda de largura.
export function responsivo(container, desenhar) {
  let largura = 0;
  const ro = new ResizeObserver(() => {
    const w = Math.floor(container.clientWidth);
    // Larguras mínimas (contêiner ainda sem layout) gerariam medidas negativas no SVG.
    if (w >= 120 && w !== largura) {
      largura = w;
      container.replaceChildren();
      desenhar(w);
    }
  });
  ro.observe(container);
}

function ticks(max, alvo = 4) {
  const bruto = max / alvo;
  const mag = 10 ** Math.floor(Math.log10(bruto || 1));
  const passo = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((p) => p >= bruto) || mag * 10;
  const lista = [];
  for (let v = 0; v <= max + 1e-9; v += passo) lista.push(Math.round(v * 100) / 100);
  if (lista[lista.length - 1] < max) lista.push(lista[lista.length - 1] + passo);
  return lista;
}

// Caminho de coluna com ponta arredondada (4px) e base reta.
function colunaPath(x, y, w, h, r = 4) {
  if (h <= 0) return "";
  const rr = Math.min(r, w / 2, h);
  return `M${x},${y + h}V${y + rr}Q${x},${y} ${x + rr},${y}H${x + w - rr}Q${x + w},${y} ${x + w},${y + rr}V${y + h}Z`;
}

// --- Colunas, uma série ------------------------------------------------------
const padraoRotulo = (d) => d.rotulo;

// dados: [{ rotulo, valor, titulo?, destaque? }]
export function colunas(container, dados, { altura = 220, cor = "var(--serie-1)", unidade = "",
  rotularMaximo = true, rotuloEixo = padraoRotulo, a11y = "" } = {}) {
  responsivo(container, (largura) => {
    const m = { t: 18, r: 8, b: 26, l: 30 };
    const w = largura - m.l - m.r, h = altura - m.t - m.b;
    const svg = el("svg", { class: "grafico", width: largura, height: altura, role: "img", "aria-label": a11y });
    container.append(svg);
    const max = Math.max(...dados.map((d) => d.valor), 1);
    const escala = ticks(max);
    const topo = escala[escala.length - 1];
    const y = (v) => m.t + h - (v / topo) * h;
    for (const t of escala) {
      el("line", { class: t === 0 ? "eixo-linha" : "grade-linha", x1: m.l, x2: m.l + w, y1: y(t), y2: y(t) }, svg);
      el("text", { x: m.l - 6, y: y(t) + 4, "text-anchor": "end" }, svg).textContent = t;
    }
    const banda = w / dados.length;
    const larg = Math.min(24, banda * 0.7);
    const passoRotulo = Math.ceil(dados.length / Math.max(1, Math.floor(w / 28)));
    const maxValor = Math.max(...dados.map((d) => d.valor));
    dados.forEach((d, i) => {
      const cx = m.l + banda * i + banda / 2;
      const g = el("g", { tabindex: "0", role: "img", "aria-label": `${d.titulo || d.rotulo}: ${d.valor}${unidade}` }, svg);
      el("path", { class: "marca-barra", d: colunaPath(cx - larg / 2, y(d.valor), larg, y(0) - y(d.valor)), fill: d.cor || cor }, g);
      el("rect", { class: "alvo", x: cx - banda / 2, y: m.t, width: banda, height: h }, g);
      const texto = rotuloEixo(d, i);
      if (texto && (dados.length <= 12 || i % passoRotulo === 0 || rotuloEixo !== padraoRotulo)) {
        el("text", { x: cx, y: altura - 8, "text-anchor": "middle" }, svg).textContent = texto;
      }
      if ((rotularMaximo && d.valor === maxValor) || d.destaque) {
        el("text", { class: "rotulo-valor", x: cx, y: y(d.valor) - 5, "text-anchor": "middle" }, svg).textContent = d.valor;
      }
      const mostrar = (ev) => {
        g.classList.add("ativo");
        mostrarTooltip(ev, d.titulo || d.rotulo, [{ valor: `${d.valor}${unidade}`, rotulo: d.legenda || "" }]);
      };
      const sair = () => { g.classList.remove("ativo"); esconderTooltip(); };
      g.addEventListener("pointermove", mostrar);
      g.addEventListener("focus", mostrar);
      g.addEventListener("pointerleave", sair);
      g.addEventListener("blur", sair);
    });
  });
}

// --- Colunas agrupadas, duas séries -----------------------------------------
// categorias: ["Casa", "Fora"]; series: [{ nome, cor, valores: [..] }]
export function colunasAgrupadas(container, categorias, series, { altura = 200, a11y = "" } = {}) {
  responsivo(container, (largura) => {
    const m = { t: 18, r: 8, b: 26, l: 30 };
    const w = largura - m.l - m.r, h = altura - m.t - m.b;
    const svg = el("svg", { class: "grafico", width: largura, height: altura, role: "img", "aria-label": a11y });
    container.append(svg);
    const max = Math.max(...series.flatMap((s) => s.valores), 1);
    const escala = ticks(max);
    const topo = escala[escala.length - 1];
    const y = (v) => m.t + h - (v / topo) * h;
    for (const t of escala) {
      el("line", { class: t === 0 ? "eixo-linha" : "grade-linha", x1: m.l, x2: m.l + w, y1: y(t), y2: y(t) }, svg);
      el("text", { x: m.l - 6, y: y(t) + 4, "text-anchor": "end" }, svg).textContent = t;
    }
    const banda = w / categorias.length;
    const larg = Math.min(24, (banda * 0.6) / series.length);
    categorias.forEach((cat, i) => {
      const centro = m.l + banda * i + banda / 2;
      const inicio = centro - (larg * series.length + 2 * (series.length - 1)) / 2;
      const g = el("g", { tabindex: "0", role: "img",
        "aria-label": `${cat}: ${series.map((s) => `${s.nome} ${s.valores[i]}`).join(", ")}` }, svg);
      series.forEach((s, k) => {
        const x = inicio + k * (larg + 2);
        el("path", { class: "marca-barra", d: colunaPath(x, y(s.valores[i]), larg, y(0) - y(s.valores[i])), fill: s.cor }, g);
        el("text", { class: "rotulo-valor", x: x + larg / 2, y: y(s.valores[i]) - 5, "text-anchor": "middle" }, svg).textContent = s.valores[i];
      });
      el("rect", { class: "alvo", x: centro - banda / 2, y: m.t, width: banda, height: h }, g);
      el("text", { x: centro, y: altura - 8, "text-anchor": "middle" }, svg).textContent = cat;
      const mostrar = (ev) => mostrarTooltip(ev, cat, series.map((s) => ({ valor: s.valores[i], rotulo: s.nome, cor: s.cor })));
      g.addEventListener("pointermove", mostrar);
      g.addEventListener("focus", mostrar);
      g.addEventListener("pointerleave", esconderTooltip);
      g.addEventListener("blur", esconderTooltip);
    });
  });
}

export function legenda(itens, tipo = "") {
  const div = document.createElement("div");
  div.className = "legenda";
  for (const { nome, cor } of itens) {
    const s = document.createElement("span");
    const i = document.createElement("i");
    if (tipo) i.className = tipo;
    i.style.background = cor;
    s.append(i, document.createTextNode(nome));
    div.append(s);
  }
  return div;
}

// --- Posição por rodada (bump chart) -----------------------------------------
// series: [{ id, nome, cor, posicoes: [38], destaque: bool }]. Eixo y invertido (1 no topo).
export function linhasPosicao(container, series, { altura = 360, rodadaAtual = 38, a11y = "" } = {}) {
  responsivo(container, (largura) => {
    const m = { t: 12, r: 92, b: 28, l: 30 };
    const w = largura - m.l - m.r, h = altura - m.t - m.b;
    const svg = el("svg", { class: "grafico", width: largura, height: altura, role: "img", "aria-label": a11y });
    container.append(svg);
    const n = series[0].posicoes.length;
    const x = (r) => m.l + ((r - 1) / (n - 1)) * w;
    const y = (p) => m.t + ((p - 1) / 19) * h;
    // Linhas nos limites das zonas de 2024: Libertadores (6º e 8º), Sul-Americana (14º) e Z4 (17º).
    for (const p of [1, 6, 8, 14, 17, 20]) {
      el("line", { class: "grade-linha", x1: m.l, x2: m.l + w, y1: y(p), y2: y(p) }, svg);
      el("text", { x: m.l - 6, y: y(p) + 4, "text-anchor": "end" }, svg).textContent = `${p}º`;
    }
    for (const r of (w < 420 ? [1, 10, 19, 29, 38] : [1, 10, 19, 20, 29, 38])) {
      el("text", { x: x(r), y: altura - 8, "text-anchor": "middle" }, svg).textContent = `R${r}`;
    }
    el("line", { class: "eixo-linha", x1: x(19.5), x2: x(19.5), y1: m.t, y2: m.t + h, "stroke-dasharray": "0" }, svg);
    const caminho = (s) => s.posicoes.map((p, i) => `${i ? "L" : "M"}${x(i + 1)},${y(p)}`).join("");
    const fundo = series.filter((s) => !s.destaque);
    const frente = series.filter((s) => s.destaque);
    for (const s of fundo) {
      el("path", { d: caminho(s), fill: "none", stroke: "var(--eixo)", "stroke-width": 1, opacity: 0.55,
        "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
    }
    // Rótulos finais: só os destacados, empurrados para não se sobreporem.
    const finais = frente.map((s) => ({ s, yy: y(s.posicoes[n - 1]) })).sort((a, b) => a.yy - b.yy);
    for (let i = 1; i < finais.length; i += 1) {
      if (finais[i].yy - finais[i - 1].yy < 14) finais[i].yy = finais[i - 1].yy + 14;
    }
    for (const s of frente) {
      el("path", { d: caminho(s), fill: "none", stroke: s.cor, "stroke-width": 2.5,
        "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
      const ultimo = s.posicoes[n - 1];
      el("circle", { cx: x(n), cy: y(ultimo), r: 4.5, fill: s.cor, stroke: "var(--superficie)", "stroke-width": 2 }, svg);
    }
    for (const { s, yy } of finais) {
      if (Math.abs(yy - y(s.posicoes[n - 1])) > 2) {
        el("line", { x1: x(n) + 6, x2: x(n) + 12, y1: y(s.posicoes[n - 1]), y2: yy, stroke: "var(--eixo)" }, svg);
      }
      el("text", { class: "rotulo-valor", x: x(n) + 14, y: yy + 4 }, svg).textContent = `${s.posicoes[n - 1]}º ${s.nome}`;
    }
    // Camada de interação: crosshair que se prende à rodada mais próxima.
    const cruz = el("line", { class: "cruz", y1: m.t, y2: m.t + h, visibility: "hidden" }, svg);
    const alvo = el("rect", { class: "alvo", x: m.l - 6, y: m.t, width: w + 12, height: h, tabindex: "0" }, svg);
    let rodadaFoco = rodadaAtual;
    const mostrar = (ev, r) => {
      cruz.setAttribute("x1", x(r)); cruz.setAttribute("x2", x(r));
      cruz.setAttribute("visibility", "visible");
      const linhas = (frente.length ? frente : series.slice(0, 5))
        .map((s) => ({ p: s.posicoes[r - 1], s }))
        .sort((a, b) => a.p - b.p)
        .map(({ p, s }) => ({ valor: `${p}º`, rotulo: s.nome, cor: s.destaque ? s.cor : "var(--eixo)" }));
      mostrarTooltip(ev, `Após a rodada ${r}`, linhas);
    };
    alvo.addEventListener("pointermove", (ev) => {
      const box = svg.getBoundingClientRect();
      const r = Math.min(n, Math.max(1, Math.round(((ev.clientX - box.left - m.l) / w) * (n - 1)) + 1));
      rodadaFoco = r;
      mostrar(ev, r);
    });
    alvo.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") {
        rodadaFoco = Math.min(n, Math.max(1, rodadaFoco + (ev.key === "ArrowLeft" ? -1 : 1)));
        mostrar({ target: alvo, type: "focus" }, rodadaFoco);
        ev.preventDefault();
      }
    });
    alvo.addEventListener("focus", () => mostrar({ target: alvo, type: "focus" }, rodadaFoco));
    const sair = () => { cruz.setAttribute("visibility", "hidden"); esconderTooltip(); };
    alvo.addEventListener("pointerleave", sair);
    alvo.addEventListener("blur", sair);
  });
}
