// Carrega o JSON exportado do PostgreSQL (scripts/exportar_web.py) e monta índices e
// estatísticas derivadas usadas pelas páginas. Nada aqui recalcula a classificação: ela vem
// pronta da view analytics.classificacao_rodada.

const ARQUIVO = "data/brasileirao2024.json";

export async function carregarDados() {
  // A prévia de arquivo único embute o JSON na página em vez de buscá-lo.
  if (globalThis.BR24_DADOS) return montar(globalThis.BR24_DADOS);
  const resposta = await fetch(ARQUIVO);
  if (!resposta.ok) throw new Error(`Falha ao carregar ${ARQUIVO}: ${resposta.status}`);
  return montar(await resposta.json());
}

export function montar(bruto) {
  const clubes = new Map(bruto.clubes.map((c) => [c.id, c]));
  const jogadores = new Map(bruto.jogadores.map((j) => [j.id, j]));

  const partidas = bruto.partidas.map((p) => ({ ...p, total: p.gm + p.gv }));
  const partidaPorId = new Map(partidas.map((p) => [p.id, p]));

  const gols = bruto.gols.map(([partida, jogador, clubeJogador, beneficiado, minuto, acrescimo, tipo]) =>
    ({ partida, jogador, clubeJogador, beneficiado, minuto, acrescimo, tipo }));
  const cartoes = bruto.cartoes.map(([partida, jogador, clube, tipo, minuto, acrescimo]) =>
    ({ partida, jogador, clube, tipo, minuto, acrescimo }));

  const golsPorPartida = agrupar(gols, (g) => g.partida);
  for (const lista of golsPorPartida.values()) {
    lista.sort((a, b) => a.minuto - b.minuto || a.acrescimo - b.acrescimo);
  }

  // Classificação: rodada (1..38) -> linhas em ordem de exibição.
  const classificacao = bruto.classificacao.map((tabela) =>
    tabela.map(([clube, pos, j, pts, v, e, d, gp, gc]) =>
      ({ clube, pos, j, pts, v, e, d, gp, gc, sg: gp - gc, aprov: j ? (100 * pts) / (3 * j) : 0 })));
  const final = classificacao[37];
  const posicaoFinal = new Map(final.map((l) => [l.clube, l.pos]));

  // Participações (clube × partida), para casa/fora, forma e sequências.
  const participacoes = [];
  for (const p of partidas) {
    participacoes.push(participacao(p, p.m, p.v, p.gm, p.gv, "Casa"));
    participacoes.push(participacao(p, p.v, p.m, p.gv, p.gm, "Fora"));
  }
  const participacoesPorClube = agrupar(participacoes, (x) => x.clube);
  for (const lista of participacoesPorClube.values()) lista.sort((a, b) => a.rodada - b.rodada);

  const estatClube = new Map();
  for (const [id, lista] of participacoesPorClube) {
    estatClube.set(id, resumoClube(lista));
  }

  const cartoesPorClube = contar(cartoes, (c) => `${c.clube}|${c.tipo}`);
  for (const [id, e] of estatClube) {
    e.amarelos = cartoesPorClube.get(`${id}|A`) || 0;
    e.vermelhos = cartoesPorClube.get(`${id}|V`) || 0;
    e.penaltis = gols.filter((g) => g.beneficiado === id && g.tipo === "Pênalti").length;
    e.golsContraAFavor = gols.filter((g) => g.beneficiado === id && g.tipo === "Contra").length;
    e.tecnicos = contarOrdenado(participacoesPorClube.get(id), (x) => x.tecnico);
  }

  return {
    meta: bruto.meta, clubes, jogadores, partidas, partidaPorId, gols, cartoes, golsPorPartida,
    classificacao, final, posicaoFinal, destinos: bruto.destinos, participacoes,
    participacoesPorClube, estatClube,
    selecao: bruto.selecao, premios: bruto.premios, creditos: bruto.creditos || [],
    campeonato: resumoCampeonato(partidas, gols, cartoes),
  };
}

function participacao(p, clube, adversario, gp, gc, mando) {
  return {
    partida: p.id, rodada: p.r, data: p.data, clube, adversario, gp, gc, mando,
    resultado: gp > gc ? "V" : gp === gc ? "E" : "D",
    pontos: gp > gc ? 3 : gp === gc ? 1 : 0,
    tecnico: mando === "Casa" ? p.tm : p.tv,
    formacao: mando === "Casa" ? p.fm : p.fv,
  };
}

function resumoClube(lista) {
  const parte = (filtro) => {
    const l = lista.filter(filtro);
    const r = { j: l.length, v: 0, e: 0, d: 0, gp: 0, gc: 0, pts: 0, semSofrer: 0 };
    for (const x of l) {
      r[x.resultado.toLowerCase()] += 1;
      r.gp += x.gp; r.gc += x.gc; r.pts += x.pontos;
      if (x.gc === 0) r.semSofrer += 1;
    }
    r.aprov = r.j ? (100 * r.pts) / (3 * r.j) : 0;
    return r;
  };
  return {
    total: parte(() => true),
    casa: parte((x) => x.mando === "Casa"),
    fora: parte((x) => x.mando === "Fora"),
    maiorSequenciaInvicta: maiorSequencia(lista, (x) => x.resultado !== "D"),
    maiorSequenciaVitorias: maiorSequencia(lista, (x) => x.resultado === "V"),
  };
}

function maiorSequencia(lista, condicao) {
  let melhor = 0, atual = 0;
  for (const x of lista) {
    atual = condicao(x) ? atual + 1 : 0;
    melhor = Math.max(melhor, atual);
  }
  return melhor;
}

export function resumoCampeonato(partidas, gols, cartoes) {
  const total = partidas.reduce((s, p) => s + p.total, 0);
  const mandante = partidas.filter((p) => p.gm > p.gv).length;
  const empates = partidas.filter((p) => p.gm === p.gv).length;
  const visitante = partidas.length - mandante - empates;
  const golsPorRodada = Array.from({ length: 38 }, (_, i) =>
    partidas.filter((p) => p.r === i + 1).reduce((s, p) => s + p.total, 0));
  const porDiferenca = [...partidas].sort((a, b) =>
    Math.abs(b.gm - b.gv) - Math.abs(a.gm - a.gv) || b.total - a.total || a.id - b.id);
  const porTotal = [...partidas].sort((a, b) => b.total - a.total || a.id - b.id);
  const faixas = ["01-15", "16-30", "31-45+", "46-60", "61-75", "76-90+"];
  const golsPorFaixa = faixas.map((f) => ({ faixa: f, gols: gols.filter((g) => faixa(g.minuto) === f).length }));
  return {
    partidas: partidas.length, gols: total, media: total / partidas.length,
    mandante, empates, visitante, golsPorRodada, golsPorFaixa,
    maiorGoleada: porDiferenca[0], jogoMaisGols: porTotal[0],
    zeroAZero: partidas.filter((p) => p.total === 0).length,
    penaltis: gols.filter((g) => g.tipo === "Pênalti").length,
    golsContra: gols.filter((g) => g.tipo === "Contra").length,
    acrescimos: gols.filter((g) => g.acrescimo > 0).length,
    amarelos: cartoes.filter((c) => c.tipo === "A").length,
    vermelhos: cartoes.filter((c) => c.tipo === "V").length,
  };
}

export function faixa(minuto) {
  if (minuto <= 15) return "01-15";
  if (minuto <= 30) return "16-30";
  if (minuto <= 45) return "31-45+";
  if (minuto <= 60) return "46-60";
  if (minuto <= 75) return "61-75";
  return "76-90+";
}

export function agrupar(lista, chave) {
  const mapa = new Map();
  for (const item of lista) {
    const k = chave(item);
    if (!mapa.has(k)) mapa.set(k, []);
    mapa.get(k).push(item);
  }
  return mapa;
}

export function contar(lista, chave) {
  const mapa = new Map();
  for (const item of lista) {
    const k = chave(item);
    mapa.set(k, (mapa.get(k) || 0) + 1);
  }
  return mapa;
}

function contarOrdenado(lista, chave) {
  return [...contar(lista, chave)].sort((a, b) => b[1] - a[1]).map(([nome, jogos]) => ({ nome, jogos }));
}

// Formatação ---------------------------------------------------------------
const fmtData = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short", timeZone: "UTC" });
const fmtDataLonga = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "long", year: "numeric", timeZone: "UTC" });
export const dataCurta = (iso) => fmtData.format(new Date(`${iso}T00:00:00Z`)).replace(".", "");
export const dataLonga = (iso) => fmtDataLonga.format(new Date(`${iso}T00:00:00Z`));
export const num = (n, casas = 0) => n.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
export const pct = (n, casas = 1) => `${num(n, casas)}%`;
export const minutoTexto = (g) => (g.acrescimo ? `${g.minuto}+${g.acrescimo}'` : `${g.minuto}'`);
export const MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
  "agosto", "setembro", "outubro", "novembro", "dezembro"];

export function embaralhar(lista, aleatorio = Math.random) {
  const a = [...lista];
  for (let i = a.length - 1; i > 0; i -= 1) {
    const j = Math.floor(aleatorio() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export const sortear = (lista, aleatorio = Math.random) => lista[Math.floor(aleatorio() * lista.length)];
