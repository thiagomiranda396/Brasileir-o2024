import { h, cabecalho, cartao, abasPagina, listaComMais, rota, filtros, faixaTitulo, faixaKpis } from "../ui.js";
import { cartaJogador } from "../carta.js";
import { coresFaixa } from "../cores.js";
import { escudo, foto } from "../imagens.js";
import { MESES, minutoTexto, dataCurta } from "../dados.js";

const RANKINGS = {
  gols: { nome: "Gols", valor: (j) => j.gols, unidade: "gols",
    nota: "Calculado gol a gol (pênaltis incluídos, gols contra excluídos) e conferido com a artilharia da Wikipédia." },
  assistencias: { nome: "Assistências", valor: (j) => j.ast, unidade: "assistências", parcial: true,
    nota: "Ranking publicado pela Wikipédia: só os primeiros colocados. Não há fonte aberta com as assistências de todos os jogadores." },
  goleiros: { nome: "Jogos sem sofrer gol", valor: (j) => j.jsg, unidade: "jogos", parcial: true,
    nota: "Goleiros com mais jogos sem sofrer gol, segundo a Wikipédia (só os primeiros colocados)." },
  penaltis: { nome: "Gols de pênalti", valor: (j) => j.pen, unidade: "pênaltis", nota: "Pênaltis convertidos." },
  amarelos: { nome: "Cartões amarelos", valor: (j) => j.ca, unidade: "amarelos", nota: "Cartões registrados na súmula de cada partida." },
  vermelhos: { nome: "Cartões vermelhos", valor: (j) => j.cv, unidade: "vermelhos", nota: "Inclui o vermelho após o segundo amarelo." },
  contra: { nome: "Gols contra", valor: (j) => j.contra, unidade: "gols contra", nota: "Gols marcados contra o próprio time." },
};

export function render(main, d, params) {
  if (params[0] === "jogador" && d.jogadores.has(params[1])) return detalhe(main, d, d.jogadores.get(params[1]));
  const aba = params[0] === "premiados" ? "premiados" : "rankings";
  main.append(cabecalho("Jogadores", "Os números de cada jogador e os premiados da temporada.", ["Buscar jogador", busca(d)]));
  main.append(abasPagina([
    ["rankings", "Rankings", rota("jogadores")],
    ["premiados", "Seleção e prêmios", rota("jogadores", "premiados")],
  ], aba));
  if (aba === "premiados") {
    main.append(h("div", { class: "grade grade-2" }, selecao(d), premios(d)));
    return;
  }
  rankings(main, d, RANKINGS[params[0]] ? params[0] : "gols");
}

function rankings(main, d, chave) {
  let clubeFiltro = "";
  const seletor = h("select", { "aria-label": "Ranking", onchange: (ev) => { location.hash = rota("jogadores", ev.target.value); } },
    Object.entries(RANKINGS).map(([k, r]) => h("option", { value: k, selected: k === chave }, r.nome)));
  const filtro = h("select", { "aria-label": "Filtrar por clube", onchange: (ev) => { clubeFiltro = ev.target.value; desenhar(); } },
    h("option", { value: "" }, "Todos os clubes"),
    [...d.clubes.values()].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR")).map((c) => h("option", { value: c.id }, c.nome)));
  const area = h("div", { class: "pilha" });
  filtros(["Ranking", seletor], ["Clube", filtro]);
  main.append(area);

  function desenhar() {
    const r = RANKINGS[chave];
    const lista = [...d.jogadores.values()]
      .filter((j) => r.valor(j) !== null && r.valor(j) > 0 && (!clubeFiltro || j.clube === clubeFiltro))
      .sort((a, b) => r.valor(b) - r.valor(a) || a.nome.localeCompare(b.nome, "pt-BR"));
    // Posição com empates compartilhados.
    let anterior = null;
    lista.forEach((j, i) => { j._pos = anterior !== null && r.valor(j) === anterior.v ? anterior.p : i + 1; anterior = { v: r.valor(j), p: j._pos }; });
    area.replaceChildren();
    if (!lista.length) {
      area.append(h("p", { class: "sem-dados" }, r.parcial ? "Nenhum jogador deste clube aparece no ranking publicado." : "Nenhum registro."));
      return;
    }
    area.append(h("div", { class: "podio" }, lista.slice(0, 3).map((j) => {
      const c = d.clubes.get(j.clube);
      return h("div", { class: "podio-item" },
        h("span", { class: "posicao-badge" }, `${j._pos}º`),
        cartaJogador(j, c, { destaque: { valor: r.valor(j), rotulo: r.unidade }, link: rota("jogadores", "jogador", j.id) }));
    })));
    const max = r.valor(lista[0]);
    const resto = lista.slice(3);
    if (resto.length) {
      area.append(cartao(null, null,
        listaComMais(resto, (j) => {
          const c = d.clubes.get(j.clube);
          return h("li", {}, h("span", { class: "mudo tab" }, `${j._pos}º`), foto(j, c),
            h("div", { style: { minWidth: 0 } },
              h("a", { class: "nome", href: rota("jogadores", "jogador", j.id), style: { display: "block" } }, j.nome),
              h("span", { class: "mudo pequeno" }, c.nome),
              h("div", { class: "barra-mini", style: { width: `${(100 * r.valor(j)) / max}%` } })),
            h("span", { class: "valor" }, r.valor(j)));
        }, { inicial: 7, rotulo: "jogadores" })));
    }
    area.append(h("p", { class: "nota" }, r.nota));
  }
  desenhar();
}

function busca(d) {
  const lista = h("datalist", { id: "lista-jogadores" },
    [...d.jogadores.values()].map((j) => h("option", { value: `${j.nome} (${d.clubes.get(j.clube).nome})` })));
  const indice = new Map([...d.jogadores.values()].map((j) => [`${j.nome} (${d.clubes.get(j.clube).nome})`, j.id]));
  const campo = h("input", { type: "search", list: "lista-jogadores", placeholder: "Buscar jogador…", "aria-label": "Buscar jogador",
    onchange: (ev) => { const id = indice.get(ev.target.value); if (id) location.hash = `#/jogadores/jogador/${id}`; } });
  return h("div", {}, campo, lista);
}

// Posições no campo (x, y em %) para o 4-4-2 da seleção.
const POSICOES_CAMPO = {
  Goleiro: [[50, 90]],
  Defensor: [[14, 70], [38, 74], [62, 74], [86, 70]],
  "Meio-campista": [[14, 44], [38, 50], [62, 50], [86, 44]],
  Atacante: [[34, 20], [66, 20]],
};

function selecao(d) {
  const campo = h("div", { class: "campo", role: "img", "aria-label": "Seleção do campeonato em 4-4-2" },
    h("div", { class: "campo-area cima" }), h("div", { class: "campo-area baixo" }));
  const usados = {};
  for (const s of d.selecao) {
    const j = d.jogadores.get(s.jogador);
    const k = usados[s.setor] = (usados[s.setor] ?? -1) + 1;
    const [x, y] = POSICOES_CAMPO[s.setor][k];
    campo.append(h("a", { class: "jogador-campo", href: `#/jogadores/jogador/${j.id}`, style: { left: `${x}%`, top: `${y}%`, textDecoration: "none" } },
      foto(j, d.clubes.get(j.clube)), h("span", {}, j.nome)));
  }
  return cartao("Seleção do campeonato", "Escolhida pela organização do campeonato (fonte: Wikipédia)", campo);
}

function premios(d) {
  const porMes = new Map();
  for (const p of d.premios) {
    if (!porMes.has(p.mes)) porMes.set(p.mes, {});
    porMes.get(p.mes)[p.premio] = d.jogadores.get(p.jogador);
  }
  const celula = (j) => (j ? h("td", { class: "esq" }, h("a", { class: "clube-inline", href: `#/jogadores/jogador/${j.id}`, style: { color: "inherit" } },
    escudo(d.clubes.get(j.clube)), h("span", {}, j.nome))) : h("td", {}, "–"));
  return cartao("Prêmios mensais", "Craque, goleiro e revelação de cada mês (fonte: Wikipédia)",
    h("div", { class: "tabela-wrap" }, h("table", {},
      h("thead", {}, h("tr", {}, h("th", { class: "esq" }, "Mês"), h("th", { class: "esq" }, "Craque"), h("th", { class: "esq" }, "Goleiro"), h("th", { class: "esq" }, "Revelação"))),
      h("tbody", {}, [...porMes].map(([mes, p]) => h("tr", {}, h("td", { class: "esq" }, MESES[mes]),
        celula(p["Craque do mês"]), celula(p["Goleiro do mês"]), celula(p["Revelação do mês"])))))));
}

function detalhe(main, d, j) {
  const c = d.clubes.get(j.clube);
  const gols = d.gols.filter((g) => g.jogador === j.id);
  const cartoes = d.cartoes.filter((k) => k.jogador === j.id);
  const homonimos = [...d.jogadores.values()].filter((o) => o.id !== j.id && o.nome_fonte === j.nome_fonte);
  const posArt = 1 + [...d.jogadores.values()].filter((o) => o.gols > j.gols).length;

  main.append(h("p", { class: "proximo" }, h("a", { href: rota("jogadores") }, "← Rankings de jogadores")));
  faixaTitulo({ titulo: j.nome, simbolo: escudo(c, "escudo-lg"), cores: coresFaixa(c), rotulo: `${c.nome} · ${j.pos || "posição não informada"}` });
  filtros(["Buscar outro jogador", busca(d)]);
  const atributos = [
    ["GOL", j.gols], ["PÊN", j.pen], ["AST", j.ast ?? "–"],
    j.pos === "Goleiro" ? ["JSG", j.jsg ?? "–"] : ["GC", j.contra],
    ["CA", j.ca], ["CV", j.cv],
  ];
  const principal = j.pos === "Goleiro" && j.jsg !== null ? { valor: j.jsg, rotulo: "sem sofrer" } : { valor: j.gols, rotulo: "gols" };
  main.append(h("div", { class: "ficha-jogador" },
    cartaJogador(j, c, { destaque: principal, atributos, classe: "carta-grande" }),
    h("div", { class: "pilha" },
      faixaKpis([
        ["Gols", j.gols, j.gols ? `${posArt}º na artilharia${j.pen ? ` · ${j.pen} de pênalti` : ""}` : "nenhum gol registrado"],
        ["Assistências", j.ast ?? "–", j.ast !== null ? "ranking da Wikipédia" : "fora do ranking publicado"],
        j.pos === "Goleiro" ? ["Jogos sem sofrer gol", j.jsg ?? "–", "ranking da Wikipédia"] : ["Gols contra", j.contra],
        ["Cartões", `${j.ca} 🟨 · ${j.cv} 🟥`],
      ], { colunas: 2 }),
      h("section", { class: "cartao" },
        h("p", { class: "clube-inline" }, escudo(c), h("a", { href: rota("clubes", c.id) }, c.nome)),
        j.nome_fonte !== j.nome ? h("p", { class: "mudo pequeno" }, `Nome na súmula: ${j.nome_fonte}`) : null,
        j.selecao ? h("p", {}, "⭐ Seleção do campeonato (carta dourada)") : null,
        h("p", { class: "nota" }, j.foto ? ["Foto: Wikimedia Commons (", h("a", { href: "#/creditos" }, "autor e licença"), "). Jogador confirmado pelo nome e pelo clube em 2024."] : "Sem foto livre confirmada: a carta mostra a camisa do clube.")))));
  if (homonimos.length) {
    main.append(h("p", { class: "aviso" }, "Também aparece com este nome por outro clube (transferência ou homônimo): ",
      homonimos.map((o) => h("a", { href: `#/jogadores/jogador/${o.id}` }, ` ${d.clubes.get(o.clube).nome}`))));
  }
  const partida = (pid) => {
    const p = d.partidaPorId.get(pid);
    return `R${p.r} · ${d.clubes.get(p.m).nome} ${p.gm} x ${p.gv} ${d.clubes.get(p.v).nome} · ${dataCurta(p.data)}`;
  };
  main.append(h("div", { class: "grade grade-2" },
    cartao("Gols", gols.length ? null : "Nenhum gol registrado",
      h("ul", { class: "lista-rank lista-eventos" }, gols.map((g) => h("li", {}, h("span", {}, "⚽"), h("span", { class: "tab" }, minutoTexto(g)),
        h("a", { class: "nome", href: `#/partidas/${d.partidaPorId.get(g.partida).r}`, style: { color: "inherit" } }, partida(g.partida)),
        h("span", { class: "mudo pequeno" }, g.tipo === "Normal" ? "" : g.tipo))))),
    cartao("Cartões", cartoes.length ? null : "Nenhum cartão registrado",
      h("ul", { class: "lista-rank lista-eventos" }, cartoes.map((k) => h("li", {}, h("span", {}, k.tipo === "A" ? "🟨" : "🟥"), h("span", { class: "tab" }, minutoTexto(k)),
        h("a", { class: "nome", href: `#/partidas/${d.partidaPorId.get(k.partida).r}`, style: { color: "inherit" } }, partida(k.partida)), h("span", {})))))));
}
