import { h, cabecalho, cartao, forma, faixaKpis, abasPagina, listaComMais, rota, faixaTitulo, filtros } from "../ui.js";
import { coresFaixa, corSerieClube, corComparacao } from "../cores.js";
import { escudo, foto } from "../imagens.js";
import { colunasAgrupadas, linhasPosicao, legenda } from "../graficos.js";
import { num, pct, dataCurta, faixa } from "../dados.js";

const ABAS = [["resumo", "Resumo"], ["elenco", "Jogadores e técnicos"], ["jogos", "Todos os jogos"]];

export function render(main, d, [id, aba]) {
  const clube = id && d.clubes.get(id.toUpperCase());
  if (!clube) return lista(main, d);
  detalhe(main, d, clube, ABAS.some(([a]) => a === aba) ? aba : "resumo");
}

function lista(main, d) {
  main.append(cabecalho("Clubes", "Escolha um clube para ver desempenho, artilheiros, técnicos e todos os jogos."));
  main.append(h("div", { class: "grade grade-4" }, d.final.map((l) => {
    const c = d.clubes.get(l.clube);
    return h("a", { class: "cartao cartao-clube", href: rota("clubes", c.id), style: { "--cor-clube": c.cor1 } },
      escudo(c, "escudo-lg"),
      h("div", {}, h("strong", {}, c.nome), h("div", { class: "mudo pequeno" }, `${l.pos}º · ${l.pts} pts · ${c.cidade}`)));
  })));
}

function detalhe(main, d, clube, aba) {
  const e = d.estatClube.get(clube.id);
  const final = d.final.find((l) => l.clube === clube.id);
  const destino = d.destinos[clube.id];
  const jogos = d.participacoesPorClube.get(clube.id);

  const seletor = h("select", { "aria-label": "Trocar de clube", onchange: (ev) => { location.hash = rota("clubes", ev.target.value, aba); } },
    [...d.clubes.values()].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"))
      .map((c) => h("option", { value: c.id, selected: c.id === clube.id }, c.nome)));

  // Faixa do topo nas cores do clube, como na página de cada time do ge.
  faixaTitulo({ titulo: clube.nome, simbolo: escudo(clube, "escudo-lg"), cores: coresFaixa(clube),
    rotulo: `${final.pos}º lugar · ${destino}` });
  filtros(["Clube", seletor]);
  main.append(h("p", { class: "intro" }, `${clube.nome_completo} · ${clube.cidade}-${clube.uf} · ${clube.estadio} (${num(clube.capacidade)} lugares)`));

  main.append(faixaKpis([
    ["Posição final", `${final.pos}º`, destino],
    ["Pontos", final.pts, `${pct(final.aprov)} de aproveitamento`],
    ["Campanha", `${final.v}V ${final.e}E ${final.d}D`, `${e.total.semSofrer} jogos sem sofrer gol`],
    ["Saldo de gols", `${final.sg > 0 ? "+" : ""}${final.sg}`, `${final.gp} marcados · ${final.gc} sofridos`],
  ]));

  main.append(abasPagina(ABAS.map(([id, nome]) => [id, nome, rota("clubes", clube.id, id)]), aba));
  const conteudo = { resumo, elenco, jogos: todosJogos }[aba];
  conteudo(main, d, clube, e, final, jogos);
}

function resumo(main, d, clube, e, final, jogos) {
  const evolucao = h("div");
  const posicoes = d.classificacao.map((t) => t.find((l) => l.clube === clube.id).pos);
  const melhorPos = Math.min(...posicoes);
  main.append(cartao("Posição rodada a rodada",
    `Melhor posição: ${melhorPos}º. Maior invencibilidade: ${e.maiorSequenciaInvicta} jogos.`, evolucao));
  const corClube = corSerieClube(clube);
  linhasPosicao(evolucao, [{ id: clube.id, nome: clube.nome, posicoes, destaque: true, cor: corClube }],
    { altura: 240, a11y: `Posição do ${clube.nome} por rodada` });

  const casaFora = h("div");
  const porFaixa = h("div");
  const series = [
    { nome: "Gols marcados", cor: corClube },
    { nome: "Gols sofridos", cor: corComparacao(corClube) },
  ];
  main.append(h("div", { class: "grade grade-2" },
    cartao("Em casa e fora", `Aproveitamento: ${pct(e.casa.aprov, 0)} em casa, ${pct(e.fora.aprov, 0)} fora`,
      casaFora, legenda(series)),
    cartao("Quando marca e quando sofre", "Gols por faixa de 15 minutos", porFaixa, legenda(series))));
  colunasAgrupadas(casaFora, ["Casa", "Fora"], [
    { ...series[0], valores: [e.casa.gp, e.fora.gp] },
    { ...series[1], valores: [e.casa.gc, e.fora.gc] },
  ], { a11y: "Gols marcados e sofridos em casa e fora" });
  const faixas = ["01-15", "16-30", "31-45+", "46-60", "61-75", "76-90+"];
  const idsPartidas = new Set(jogos.map((j) => j.partida));
  const golsJogos = d.gols.filter((g) => idsPartidas.has(g.partida));
  colunasAgrupadas(porFaixa, faixas.map((f) => `${f}'`), [
    { ...series[0], valores: faixas.map((f) => golsJogos.filter((g) => g.beneficiado === clube.id && faixa(g.minuto) === f).length) },
    { ...series[1], valores: faixas.map((f) => golsJogos.filter((g) => g.beneficiado !== clube.id && faixa(g.minuto) === f).length) },
  ], { a11y: "Gols por faixa de minutos" });
}

function elenco(main, d, clube, e, final) {
  const jogadores = [...d.jogadores.values()].filter((j) => j.clube === clube.id);
  const artilheiros = jogadores.filter((j) => j.gols > 0).sort((a, b) => b.gols - a.gols || a.nome.localeCompare(b.nome));
  const advertidos = jogadores.filter((j) => j.ca + j.cv > 0).sort((a, b) => (b.cv * 3 + b.ca) - (a.cv * 3 + a.ca));
  const linhaJog = (j, valor) => h("li", {},
    h("span", {}), foto(j, clube), h("a", { class: "nome", href: rota("jogadores", "jogador", j.id) }, j.nome), h("span", { class: "valor" }, valor));
  main.append(h("div", { class: "grade grade-3" },
    cartao("Artilheiros", `${final.gp} gols${e.golsContraAFavor ? `, ${e.golsContraAFavor} deles contra` : ""}`,
      listaComMais(artilheiros, (j) => linhaJog(j, j.gols), { inicial: 6, rotulo: "jogadores" })),
    cartao("Mais advertidos", `${e.amarelos} amarelos e ${e.vermelhos} vermelhos no campeonato`,
      listaComMais(advertidos, (j) => linhaJog(j, `${j.ca}🟨${j.cv ? ` ${j.cv}🟥` : ""}`), { inicial: 6, rotulo: "jogadores" })),
    cartao("Técnicos", "Jogos no comando (nomes como na súmula)",
      h("ol", { class: "lista-rank" }, e.tecnicos.map((t) => h("li", {}, h("span", {}), h("span", {}, "🧑‍💼"), h("span", { class: "nome" }, t.nome), h("span", { class: "valor" }, t.jogos)))))));
}

function todosJogos(main, d, clube, e, final, jogos) {
  const linhas = jogos.map((x) => {
    const p = d.partidaPorId.get(x.partida);
    const adv = d.clubes.get(x.adversario);
    return h("tr", { class: "clicavel", onclick: () => { location.hash = rota("partidas", p.r); } },
      h("td", { class: "esq mudo" }, `R${p.r}`), h("td", { class: "esq mudo" }, dataCurta(p.data)),
      h("td", { class: "esq" }, h("span", { class: "clube-inline" }, escudo(adv), h("span", {}, adv.nome))),
      h("td", { class: "esq mudo" }, x.mando === "Casa" ? "Casa" : "Fora"),
      h("td", {}, h("strong", {}, `${x.gp} x ${x.gc}`)),
      h("td", { class: "esq" }, forma([x.resultado])));
  });
  main.append(cartao(null, null,
    h("div", { class: "tabela-wrap" }, h("table", {},
      h("thead", {}, h("tr", {}, h("th", { class: "esq" }, "Rodada"), h("th", { class: "esq" }, "Data"),
        h("th", { class: "esq" }, "Adversário"), h("th", { class: "esq" }, "Mando"), h("th", {}, "Placar"), h("th", { class: "esq" }, "Resultado"))),
      h("tbody", {}, linhas)))));
}
