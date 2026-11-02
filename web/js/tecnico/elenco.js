// Prancheta 2024: força de clubes e jogadores derivada do desempenho real no Brasileirão 2024.
//
// Módulo puro (sem DOM): recebe os dados montados por dados.js e é usado pela página de
// minijogos e pelos testes em Node. A base de cada clube vem dos pontos na tabela final; o
// ataque e a defesa reais (gols pró e contra) puxam a nota dos setores; gols, assistências,
// jogos sem sofrer gol, seleção do campeonato e prêmios do mês sobem a nota de cada jogador.

import { contar } from "../dados.js";

export const SETORES = { GOL: "Goleiro", DEF: "Defensor", MEI: "Meio-campo", ATA: "Atacante" };
export const SIGLA_SETOR = { GOL: "GOL", DEF: "DEF", MEI: "MEI", ATA: "ATA" };
const SETOR_DA_POSICAO = { Goleiro: "GOL", Zagueiro: "DEF", Lateral: "DEF", "Meio-campo": "MEI", Atacante: "ATA" };
export const setorNatural = (j) => SETOR_DA_POSICAO[j.pos] || "MEI";

// Perda de nota ao jogar fora de posição: PENALIDADE[setor natural][setor da vaga].
export const PENALIDADE = {
  GOL: { GOL: 0, DEF: -25, MEI: -28, ATA: -28 },
  DEF: { GOL: -30, DEF: 0, MEI: -7, ATA: -13 },
  MEI: { GOL: -30, DEF: -7, MEI: 0, ATA: -4 },
  ATA: { GOL: -30, DEF: -14, MEI: -5, ATA: 0 },
};

// linhas: da defesa para o ataque (a primeira é a defesa, a última o ataque, o resto é meio).
// atq/sofre multiplicam os gols esperados a favor e contra.
export const FORMACOES = {
  "4-2-3-1": { linhas: [4, 2, 3, 1], atq: 1.0, sofre: 0.97, estilo: "Equilibrado, protege a defesa" },
  "4-4-2": { linhas: [4, 4, 2], atq: 1.0, sofre: 1.0, estilo: "Equilibrado" },
  "4-3-3": { linhas: [4, 3, 3], atq: 1.07, sofre: 1.05, estilo: "Ofensivo, pelas pontas" },
  "3-5-2": { linhas: [3, 5, 2], atq: 1.04, sofre: 1.03, estilo: "Domina o meio-campo" },
  "3-4-3": { linhas: [3, 4, 3], atq: 1.12, sofre: 1.1, estilo: "Muito ofensivo" },
  "4-1-4-1": { linhas: [4, 1, 4, 1], atq: 0.95, sofre: 0.94, estilo: "Cauteloso" },
  "5-3-2": { linhas: [5, 3, 2], atq: 0.93, sofre: 0.92, estilo: "Defensivo" },
  "5-4-1": { linhas: [5, 4, 1], atq: 0.86, sofre: 0.86, estilo: "Retranca" },
};

export const POSTURAS = {
  defensiva: { rotulo: "Defensiva", atq: 0.8, sofre: 0.8, desgaste: 0.85, faltas: 1.15 },
  equilibrada: { rotulo: "Equilibrada", atq: 1, sofre: 1, desgaste: 1, faltas: 1 },
  ofensiva: { rotulo: "Ofensiva", atq: 1.2, sofre: 1.15, desgaste: 1.2, faltas: 0.95 },
};

export function setoresDaFormacao(nome) {
  const { linhas } = FORMACOES[nome];
  return ["GOL", ...linhas.flatMap((n, i) =>
    Array(n).fill(i === 0 ? "DEF" : i === linhas.length - 1 ? "ATA" : "MEI"))];
}

// Vagas com posição no campo (x, y em %; o próprio gol embaixo).
export function vagasDaFormacao(nome) {
  const { linhas } = FORMACOES[nome];
  const vagas = [{ setor: "GOL", x: 50, y: 90 }];
  linhas.forEach((n, i) => {
    const y = 72 - (56 * i) / Math.max(1, linhas.length - 1);
    const passo = n > 1 ? Math.min(24, 80 / (n - 1)) : 0;
    const setor = i === 0 ? "DEF" : i === linhas.length - 1 ? "ATA" : "MEI";
    for (let k = 0; k < n; k += 1) vagas.push({ setor, x: 50 + (k - (n - 1) / 2) * passo, y });
  });
  return vagas;
}

function contagem(nome) {
  const s = setoresDaFormacao(nome);
  return { DEF: s.filter((x) => x === "DEF").length, MEI: s.filter((x) => x === "MEI").length, ATA: s.filter((x) => x === "ATA").length };
}

// Formação real mais usada -> a suportada mais parecida (mesmo nº de defensores e atacantes, se houver).
export function formacaoMaisProxima(real) {
  if (real in FORMACOES) return real;
  const partes = String(real || "").split("-").map(Number).filter(Number.isFinite);
  if (partes.length < 3) return "4-2-3-1";
  const alvo = { DEF: partes[0], ATA: partes[partes.length - 1] };
  let melhor = "4-2-3-1", menor = Infinity;
  for (const nome of Object.keys(FORMACOES)) {
    const c = contagem(nome);
    const dist = 2 * Math.abs(c.DEF - alvo.DEF) + Math.abs(c.ATA - alvo.ATA);
    if (dist < menor) { menor = dist; melhor = nome; }
  }
  return melhor;
}

function hash(texto) {
  let x = 2166136261;
  for (const ch of texto) x = Math.imul(x ^ ch.codePointAt(0), 16777619);
  return x >>> 0;
}

const limitar = (v, min, max) => Math.max(min, Math.min(max, v));

export function prepararElencos(d) {
  const linhas = d.final;
  const ptsMin = Math.min(...linhas.map((l) => l.pts));
  const ptsMax = Math.max(...linhas.map((l) => l.pts));
  const mediaGp = linhas.reduce((s, l) => s + l.gp, 0) / linhas.length;
  const mediaGc = linhas.reduce((s, l) => s + l.gc, 0) / linhas.length;
  const premios = contar(d.premios, (p) => p.jogador);
  const selecao = new Set(d.selecao.map((s) => s.jogador));

  const porClube = new Map([...d.clubes.keys()].map((id) => [id, []]));
  for (const j of d.jogadores.values()) porClube.get(j.clube)?.push(j);

  const times = new Map();
  for (const l of linhas) {
    const clube = d.clubes.get(l.clube);
    const base = 60 + (18 * (l.pts - ptsMin)) / (ptsMax - ptsMin);
    const ajusteAtaque = ((l.gp - mediaGp) / mediaGp) * 8;
    const ajusteDefesa = ((mediaGc - l.gc) / mediaGc) * 8;

    // Goleiro titular: quem mais aparece (jogos sem sofrer gol, depois cartões e gols).
    const goleiros = porClube.get(l.clube).filter((j) => setorNatural(j) === "GOL")
      .sort((a, b) => (b.jsg ?? -1) - (a.jsg ?? -1) || (b.ca + b.cv) - (a.ca + a.cv) || a.nome.localeCompare(b.nome));
    const titularGol = goleiros[0]?.id;

    const jogadores = porClube.get(l.clube).map((j) => {
      const setor = setorNatural(j);
      let nota = base + (setor === "ATA" || setor === "MEI" ? ajusteAtaque : ajusteDefesa);
      if (setor === "ATA") nota += Math.min(9, j.gols * 0.75);
      else if (setor === "MEI") nota += Math.min(7, j.gols * 0.7);
      else if (setor === "DEF") nota += Math.min(3, j.gols * 0.7);
      if (j.ast !== null) nota += Math.min(4, j.ast * 0.4);
      if (j.jsg !== null) nota += Math.min(5, j.jsg * 0.4);
      if (selecao.has(j.id)) nota += 4;
      nota += Math.min(4.5, 1.5 * (premios.get(j.id) || 0));
      // Os dados só listam quem marcou ou levou cartão: pouca participação sugere reserva.
      if (setor === "GOL") {
        if (j.id !== titularGol) nota -= 6;
      } else {
        const participacao = j.gols + j.ca + 2 * j.cv + (j.ast ?? 0);
        nota += participacao <= 1 ? -5 : participacao === 2 ? -3 : participacao <= 4 ? -1 : participacao <= 7 ? 0 : 1;
      }
      nota += (hash(j.id) % 5) - 2;
      return {
        id: j.id, nome: j.nome, clube: j.clube, setor, nota: Math.round(limitar(nota, 48, 94)),
        gols: j.gols, pen: j.pen, ca: j.ca, cv: j.cv, ast: j.ast, jsg: j.jsg, selecao: selecao.has(j.id), ref: j,
      };
    }).sort((a, b) => ordemSetor(a.setor) - ordemSetor(b.setor) || b.nota - a.nota || a.nome.localeCompare(b.nome));

    const est = d.estatClube.get(l.clube);
    const formacoes = contar(d.participacoesPorClube.get(l.clube).filter((x) => x.formacao), (x) => x.formacao);
    const formacaoReal = [...formacoes].sort((a, b) => b[1] - a[1])[0]?.[0];
    const time = {
      id: l.clube, clube, posicao: l.pos, pts: l.pts, v: l.v, e: l.e, d: l.d, gp: l.gp, gc: l.gc,
      destino: d.destinos[l.clube], tecnico: est.tecnicos[0]?.nome || "—",
      formacao: formacaoMaisProxima(formacaoReal), formacaoReal: formacaoReal || "—",
      jogadores, porId: new Map(jogadores.map((j) => [j.id, j])),
    };
    const melhor = escalarAutomatico(time, time.formacao);
    time.forca = Math.round(melhor.reduce((s, id, i) => s + notaNaVaga(time.porId.get(id), setoresDaFormacao(time.formacao)[i]), 0) / 11);
    times.set(l.clube, time);
  }
  return times;
}

const ordemSetor = (s) => ["GOL", "DEF", "MEI", "ATA"].indexOf(s);

export const notaNaVaga = (j, setor) => j.nota + PENALIDADE[j.setor][setor];
export const fatorEnergia = (energia) => 0.8 + (0.2 * energia) / 100;

// Escala os 11 de maior nota efetiva: primeiro quem joga na posição de origem, depois o resto
// (com a penalidade de fora de posição). Devolve os ids na ordem das vagas.
export function escalarAutomatico(time, formacao, { energia = {}, indisponiveis = new Set() } = {}) {
  const setores = setoresDaFormacao(formacao);
  const disponiveis = time.jogadores.filter((j) => !indisponiveis.has(j.id));
  const valor = (j, setor) => notaNaVaga(j, setor) * fatorEnergia(energia[j.id] ?? 100);
  const usados = new Set();
  const escalacao = Array(11).fill(null);
  for (const setor of ["GOL", "ATA", "DEF", "MEI"]) {
    const vagas = setores.map((s, i) => (s === setor ? i : -1)).filter((i) => i >= 0);
    const naturais = disponiveis.filter((j) => j.setor === setor).sort((a, b) => valor(b, setor) - valor(a, setor));
    for (const i of vagas) {
      const j = naturais.find((x) => !usados.has(x.id));
      if (j) { escalacao[i] = j.id; usados.add(j.id); }
    }
  }
  setores.forEach((setor, i) => {
    if (escalacao[i]) return;
    const j = disponiveis.filter((x) => !usados.has(x.id)).sort((a, b) => valor(b, setor) - valor(a, setor))[0];
    if (j) { escalacao[i] = j.id; usados.add(j.id); }
  });
  return escalacao;
}

// Forças por setor de quem está em campo: [{ jogador, setor (da vaga), energia }].
export function forcasEmCampo(emCampo, formacao) {
  const soma = { GOL: [], DEF: [], MEI: [], ATA: [] };
  for (const x of emCampo) soma[x.setor].push(notaNaVaga(x.jogador, x.setor) * fatorEnergia(x.energia));
  const media = (l) => (l.length ? l.reduce((s, v) => s + v, 0) / l.length : null);
  const GOL = media(soma.GOL) ?? 40;
  const DEF = media(soma.DEF) ?? (media(soma.MEI) ?? 50) - 6;
  const MEI = media(soma.MEI) ?? (DEF + (media(soma.ATA) ?? DEF)) / 2 - 4;
  const ATA = media(soma.ATA) ?? MEI - 3;
  const extraMeio = formacao ? (contagem(formacao).MEI - 4) * 1.5 : 0;
  return {
    GOL, DEF, MEI, ATA,
    ataque: 0.5 * ATA + 0.35 * MEI + 0.15 * DEF,
    defesa: 0.5 * DEF + 0.2 * MEI + 0.3 * GOL,
    meio: MEI + extraMeio,
  };
}
