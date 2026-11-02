import { h, cabecalho, secao, forma, filtros, ZONAS, lerPreferencia, gravarPreferencia } from "../ui.js";
import { escudo } from "../imagens.js";
import { linhasPosicao, legenda } from "../graficos.js";
import { pct } from "../dados.js";

const CORES = ["var(--serie-1)", "var(--serie-2)", "var(--serie-3)"];

export function render(main, d) {
  let rodada = 38;
  let mando = "Geral";
  let tocando = null;

  main.append(cabecalho("Classificação",
    "Use a barra lateral para ver a tabela após qualquer rodada, ou aperte Play para assistir ao campeonato."));

  const rotulo = h("h2", {});
  const valorRodada = h("span", { class: "valor-filtro" });
  const slider = h("input", { type: "range", min: "1", max: "38", value: "38", "aria-label": "Rodada" });
  const play = h("button", { class: "botao", type: "button" }, "▶ Play");
  const abas = h("div", { class: "abas", role: "group", "aria-label": "Mando" },
    ["Geral", "Casa", "Fora"].map((m) => h("button", { type: "button", "aria-pressed": String(m === mando), onclick: () => {
      mando = m;
      for (const b of abas.children) b.setAttribute("aria-pressed", String(b.textContent === m));
      desenhar();
    } }, m)));

  const corpo = h("tbody");
  const tabela = h("div", { class: "tabela-wrap" }, h("table", {},
    h("thead", {}, h("tr", {},
      h("th", { class: "esq" }, "#"), h("th", { class: "esq" }, "Clube"), h("th", { title: "Pontos" }, "P"),
      h("th", { title: "Jogos" }, "J"), h("th", { title: "Vitórias" }, "V"), h("th", { title: "Empates" }, "E"),
      h("th", { title: "Derrotas" }, "D"), h("th", { title: "Gols pró" }, "GP"), h("th", { title: "Gols contra" }, "GC"),
      h("th", { title: "Saldo de gols" }, "SG"), h("th", { title: "Aproveitamento" }, "%"),
      h("th", { title: "Variação de posição em relação à rodada anterior" }, "±"),
      h("th", { class: "esq" }, "Últimos 5"))),
    corpo));

  const aviso = h("p", { class: "nota" });
  filtros(["Rodada", h("div", { class: "pilha-filtro" }, valorRodada, slider, play)], ["Jogos", abas]);
  main.append(h("section", { class: "cartao" }, rotulo, tabela,
    legenda([
      { nome: "Campeão e Libertadores (fase de grupos)", cor: "var(--zona-lib)" },
      { nome: "Libertadores (2ª fase)", cor: "var(--zona-lib2)" },
      { nome: "Sul-Americana", cor: "var(--zona-sula)" },
      { nome: "Rebaixamento", cor: "var(--zona-rebaixado)" },
    ]),
    aviso));

  function tabelaMando(n) {
    if (mando === "Geral") return d.classificacao[n - 1];
    const linhas = [];
    for (const [clube, lista] of d.participacoesPorClube) {
      const l = { clube, j: 0, pts: 0, v: 0, e: 0, d: 0, gp: 0, gc: 0 };
      for (const x of lista) {
        if (x.rodada > n || x.mando !== mando) continue;
        l.j += 1; l.pts += x.pontos; l.gp += x.gp; l.gc += x.gc;
        l[x.resultado.toLowerCase()] += 1;
      }
      l.sg = l.gp - l.gc;
      l.aprov = l.j ? (100 * l.pts) / (3 * l.j) : 0;
      linhas.push(l);
    }
    const chave = (l) => [l.pts, l.v, l.sg, l.gp];
    linhas.sort((a, b) => {
      const ka = chave(a), kb = chave(b);
      for (let i = 0; i < 4; i += 1) if (ka[i] !== kb[i]) return kb[i] - ka[i];
      return d.clubes.get(a.clube).nome.localeCompare(d.clubes.get(b.clube).nome, "pt-BR");
    });
    let anterior = null;
    linhas.forEach((l, i) => {
      l.pos = anterior && chave(anterior).join() === chave(l).join() ? anterior.pos : i + 1;
      anterior = l;
    });
    return linhas;
  }

  function desenhar() {
    rotulo.textContent = `${mando === "Geral" ? "Classificação" : `Só jogos ${mando === "Casa" ? "em casa" : "fora"}`} após a rodada ${rodada}`;
    valorRodada.textContent = `Rodada ${rodada}`;
    slider.value = String(rodada);
    const linhas = tabelaMando(rodada);
    const antes = rodada > 1 ? new Map(tabelaMando(rodada - 1).map((l) => [l.clube, l.pos])) : null;
    corpo.replaceChildren(...linhas.map((l, i) => {
      const clube = d.clubes.get(l.clube);
      const zona = mando === "Geral" ? zonaPorOrdem(i + 1) : "";
      const varia = antes ? antes.get(l.clube) - l.pos : 0;
      const ultimos = d.participacoesPorClube.get(l.clube)
        .filter((x) => x.rodada <= rodada && (mando === "Geral" || x.mando === mando)).slice(-5).map((x) => x.resultado);
      return h("tr", { class: "clicavel", onclick: () => { location.hash = `#/clubes/${clube.id}`; } },
        h("td", { class: "esq" }, h("span", { class: "pos" }, h("i", { class: `zona ${zona}` }), `${l.pos}`)),
        h("td", { class: "esq" }, h("a", { class: "clube-inline", href: `#/clubes/${clube.id}`, style: { color: "inherit", textDecoration: "none" } },
          escudo(clube), h("span", {}, clube.nome))),
        h("td", {}, h("strong", {}, l.pts)), h("td", {}, l.j), h("td", {}, l.v), h("td", {}, l.e), h("td", {}, l.d),
        h("td", {}, l.gp), h("td", {}, l.gc), h("td", {}, l.sg > 0 ? `+${l.sg}` : l.sg), h("td", {}, pct(l.aprov, 0)),
        h("td", { class: varia > 0 ? "variacao-sobe" : varia < 0 ? "variacao-desce" : "mudo" },
          varia > 0 ? `▲${varia}` : varia < 0 ? `▼${-varia}` : "–"),
        h("td", { class: "esq" }, forma(ultimos)));
    }));
    aviso.textContent = rodada === 38 && mando === "Geral"
      ? "Classificação final conferida com a tabela oficial da CBF. Botafogo e Flamengo, campeões da Libertadores e da Copa do Brasil, ampliaram a zona da Libertadores até o 8º colocado."
      : `${d.meta.aviso_classificacao} Jogos adiados contam na rodada original. As cores das zonas seguem as vagas finais de 2024.`;
  }

  function zonaPorOrdem(ordem) {
    const clubeFinal = d.final[ordem - 1].clube;
    return ZONAS[d.destinos[clubeFinal]] || "";
  }

  slider.addEventListener("input", () => { rodada = Number(slider.value); parar(); desenhar(); });
  function parar() {
    if (tocando) { clearInterval(tocando); tocando = null; play.textContent = "▶ Play"; }
  }
  play.addEventListener("click", () => {
    if (tocando) return parar();
    if (rodada === 38) rodada = 1;
    play.textContent = "❚❚ Pausar";
    desenhar();
    tocando = setInterval(() => {
      if (!document.body.contains(play)) return parar();
      if (rodada >= 38) return parar();
      rodada += 1;
      desenhar();
    }, 650);
  });
  desenhar();

  // Evolução das posições
  const escolhidos = lerPreferencia("br24-evolucao", ["BOT", "PAL", "FLA"]);
  const ordenados = [...d.clubes.values()].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  const grafico = h("div");
  const leg = h("div");
  const seletores = h("div", { class: "pilha-filtro" },
    escolhidos.map((id, k) => h("select", { "aria-label": `Clube ${k + 1}`, onchange: (ev) => {
      escolhidos[k] = ev.target.value;
      gravarPreferencia("br24-evolucao", escolhidos);
      desenharEvolucao();
    } }, h("option", { value: "" }, "—"), ordenados.map((c) => h("option", { value: c.id, selected: c.id === id }, c.nome)))));
  filtros(["Clubes no gráfico de evolução", seletores]);
  main.append(secao("Evolução das posições", "Compare até três clubes (escolha na barra lateral); passe o mouse ou use as setas do teclado para percorrer as rodadas.",
    h("section", { class: "cartao" }, grafico, leg)));

  function desenharEvolucao() {
    const posicoes = new Map([...d.clubes.keys()].map((id) => [id, []]));
    for (const tabelaR of d.classificacao) for (const l of tabelaR) posicoes.get(l.clube).push(l.pos);
    const series = [...d.clubes.values()].map((c) => {
      const k = escolhidos.indexOf(c.id);
      return { id: c.id, nome: c.nome, posicoes: posicoes.get(c.id), destaque: k >= 0, cor: CORES[k] };
    });
    grafico.replaceChildren();
    linhasPosicao(grafico, series, { a11y: "Posição dos clubes por rodada" });
    leg.replaceChildren(legenda([
      ...escolhidos.filter(Boolean).map((id) => ({ nome: d.clubes.get(id).nome, cor: CORES[escolhidos.indexOf(id)] })),
      { nome: "Demais clubes", cor: "var(--eixo)" },
    ], "linha"));
  }
  desenharEvolucao();
}
