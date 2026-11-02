// Prancheta 2024: motor de partida minuto a minuto e disputa de pênaltis.
//
// Módulo puro (sem DOM). A cada minuto, cada time tem uma chance de gol proporcional aos gols
// esperados no jogo, que dependem do ataque de um contra a defesa do outro (notas de quem está
// em campo, com desgaste), do meio-campo, da formação, da postura e de expulsões.

import { POSTURAS, FORMACOES, setoresDaFormacao, forcasEmCampo, notaNaVaga, fatorEnergia } from "./elenco.js";

const GOLS_BASE = 1.15;       // gols esperados por time entre forças iguais
const ESCALA = 40;            // diferença ataque x defesa que multiplica os gols esperados por e
const CHANCES_POR_GOL = 7;    // finalizações por gol
const DESGASTE = 0.42;        // energia perdida por minuto, postura equilibrada
export const MAX_SUBSTITUICOES = 5;

const limitar = (v, min, max) => Math.max(min, Math.min(max, v));
const escolher = (lista, aleatorio) => lista[Math.floor(aleatorio() * lista.length)];

function ponderado(itens, peso, aleatorio) {
  const pesos = itens.map(peso);
  let r = aleatorio() * pesos.reduce((s, x) => s + x, 0);
  for (let i = 0; i < itens.length; i += 1) {
    r -= pesos[i];
    if (r <= 0) return itens[i];
  }
  return itens[itens.length - 1];
}

// cfg: { time, titulares: [11 ids na ordem das vagas], formacao, postura, energia: {id: 0..100},
//        indisponiveis: Set, controlado }
export function criarPartida(casa, fora, aleatorio = Math.random) {
  const lado = (cfg) => {
    const setores = setoresDaFormacao(cfg.formacao);
    const titulares = new Set(cfg.titulares);
    const fora = cfg.indisponiveis || new Set();
    const energia = {};
    for (const j of cfg.time.jogadores) energia[j.id] = cfg.energia?.[j.id] ?? 100;
    return {
      time: cfg.time, controlado: Boolean(cfg.controlado), formacao: cfg.formacao,
      postura: cfg.postura || "equilibrada", posturaInicial: cfg.postura || "equilibrada",
      emCampo: cfg.titulares.map((id, i) => ({ jogador: cfg.time.porId.get(id), setor: setores[i], vaga: i })),
      banco: cfg.time.jogadores.filter((j) => !titulares.has(j.id) && !fora.has(j.id)).map((j) => j.id),
      energia, jogaram: new Set(cfg.titulares), amarelos: new Set(), expulsos: [], subs: 0, gols: 0,
      marcadores: [], estat: { finalizacoes: 0, noAlvo: 0, amarelos: 0, vermelhos: 0, posse: 0 },
    };
  };
  return {
    lados: [lado(casa), lado(fora)], estado: "pre", periodo: 1, minuto: 0, extra: 0,
    acrescimos: [1 + Math.floor(aleatorio() * 3), 2 + Math.floor(aleatorio() * 4)],
    minutosJogados: 0, eventos: [], aleatorio,
  };
}

export function rotuloMinuto(p) {
  if (p.estado === "pre") return "0'";
  return p.extra ? `${p.periodo === 1 ? 45 : 90}+${p.extra}'` : `${p.minuto}'`;
}

export function forcasDoLado(l) {
  return forcasEmCampo(l.emCampo.map((x) => ({ jogador: x.jogador, setor: x.setor, energia: l.energia[x.jogador.id] })), l.formacao);
}

function golsEsperados(p, i, f) {
  const eu = p.lados[i], ele = p.lados[1 - i];
  const diferencaJogadores = ele.expulsos.length - eu.expulsos.length;
  return GOLS_BASE
    * Math.exp((f[i].ataque - f[1 - i].defesa) / ESCALA)
    * Math.exp((f[i].meio - f[1 - i].meio) / 120)
    * FORMACOES[eu.formacao].atq * FORMACOES[ele.formacao].sofre
    * POSTURAS[eu.postura].atq * POSTURAS[ele.postura].sofre
    * 1.25 ** diferencaJogadores;
}

// Probabilidades de vitória/empate/derrota em 90 minutos (Poisson), para o pré-jogo.
export function previsao(casa, fora) {
  const p = criarPartida(casa, fora, () => 0.5);
  const f = p.lados.map(forcasDoLado);
  const l = [golsEsperados(p, 0, f), golsEsperados(p, 1, f)];
  const poisson = (lam) => {
    const ps = [Math.exp(-lam)];
    for (let k = 1; k <= 10; k += 1) ps.push((ps[k - 1] * lam) / k);
    return ps;
  };
  const [pa, pb] = l.map(poisson);
  let vitoria = 0, empate = 0;
  for (let a = 0; a <= 10; a += 1) {
    for (let b = 0; b <= 10; b += 1) {
      if (a > b) vitoria += pa[a] * pb[b];
      else if (a === b) empate += pa[a] * pb[b];
    }
  }
  return { gols: l, vitoria, empate, derrota: Math.max(0, 1 - vitoria - empate), forcas: f };
}

export function avancar(p) {
  const novos = [];
  const ev = (e) => {
    const x = { min: rotuloMinuto(p), ...e };
    p.eventos.push(x);
    novos.push(x);
  };
  if (p.estado === "fim") return novos;
  const [A, B] = p.lados;
  const inicio = p.estado === "pre" ? `Bola rolando! ${A.time.clube.nome} x ${B.time.clube.nome}.`
    : p.estado === "intervalo" ? "Começa o segundo tempo." : null;
  if (p.estado === "intervalo") {
    p.periodo = 2; p.minuto = 45; p.extra = 0;
  }
  p.estado = "jogo";
  const limite = p.periodo === 1 ? 45 : 90;
  if (p.minuto < limite) p.minuto += 1;
  else p.extra += 1;
  if (inicio) ev({ tipo: "apito", texto: inicio });
  p.minutosJogados += 1;
  jogarMinuto(p, ev);
  if (p.minuto === limite && p.extra === 0) {
    ev({ tipo: "info", texto: `Fim do tempo normal: ${p.acrescimos[p.periodo - 1]} minutos de acréscimo.` });
  }
  if (p.minuto === limite && p.extra === p.acrescimos[p.periodo - 1]) {
    if (p.periodo === 1) {
      p.estado = "intervalo";
      ev({ tipo: "apito", texto: `Intervalo: ${A.time.clube.nome} ${A.gols} x ${B.gols} ${B.time.clube.nome}.` });
    } else {
      p.estado = "fim";
      ev({ tipo: "apito", texto: `Fim de jogo: ${A.time.clube.nome} ${A.gols} x ${B.gols} ${B.time.clube.nome}.` });
    }
  }
  return novos;
}

function jogarMinuto(p, ev) {
  const r = p.aleatorio;
  for (const l of p.lados) {
    const desgaste = DESGASTE * POSTURAS[l.postura].desgaste;
    for (const x of l.emCampo) {
      const id = x.jogador.id;
      l.energia[id] = Math.max(0, l.energia[id] - desgaste * (0.8 + 0.4 * r()));
    }
  }
  p.lados.forEach((l, i) => { if (!l.controlado) decidirIA(p, i, ev); });

  const f = p.lados.map(forcasDoLado);
  const ajustePosse = { defensiva: -0.05, equilibrada: 0, ofensiva: 0.04 };
  const posse = limitar(0.5 + (f[0].meio - f[1].meio) / 80
    + ajustePosse[p.lados[0].postura] - ajustePosse[p.lados[1].postura], 0.28, 0.72);
  p.lados[0].estat.posse += posse;
  p.lados[1].estat.posse += 1 - posse;

  for (const i of r() < 0.5 ? [0, 1] : [1, 0]) {
    const chanceGol = golsEsperados(p, i, f) / 90;
    const sorteio = r();
    if (sorteio < chanceGol) gol(p, i, ev);
    else if (sorteio < chanceGol * CHANCES_POR_GOL) finalizacao(p, i, ev);
  }
  p.lados.forEach((l, i) => {
    const sorteio = r();
    const amarelo = (2.3 / 90) * POSTURAS[l.postura].faltas;
    if (sorteio < amarelo) cartao(p, i, false, ev);
    else if (sorteio < amarelo + 0.07 / 90) cartao(p, i, true, ev);
  });
}

const PESO_GOL = { GOL: 0, DEF: 0.7, MEI: 2.2, ATA: 5 };
const PESO_PASSE = { GOL: 0.1, DEF: 1, MEI: 3, ATA: 2 };

function sortearAutor(l, r, excluir = null) {
  const candidatos = l.emCampo.filter((x) => x.setor !== "GOL" && x.jogador !== excluir);
  if (!candidatos.length) return l.emCampo[0].jogador;
  return ponderado(candidatos, (x) => PESO_GOL[x.setor] * (1 + x.jogador.gols * 0.25) * fatorEnergia(l.energia[x.jogador.id]), r).jogador;
}

const goleiroDe = (l) => (l.emCampo.find((x) => x.setor === "GOL") || l.emCampo[0]).jogador;
export const nomeCurto = (nome) => {
  const partes = nome.split(/\s+/);
  if (partes.length <= 2 || nome.length <= 18) return nome;
  const util = partes.filter((w, k) => k === 0 || !/^(de|da|do|dos|das|del|la|e)$/i.test(w));
  return util.slice(0, 2).join(" ");
};

function gol(p, i, ev) {
  const r = p.aleatorio;
  const l = p.lados[i];
  const penalti = r() < 0.08;
  let autor;
  if (penalti) {
    autor = [...l.emCampo].filter((x) => x.setor !== "GOL")
      .sort((a, b) => (b.jogador.pen * 10 + b.jogador.nota) - (a.jogador.pen * 10 + a.jogador.nota))[0]?.jogador || sortearAutor(l, r);
  } else {
    autor = sortearAutor(l, r);
  }
  const candidatosPasse = l.emCampo.filter((x) => x.jogador !== autor);
  const passe = !penalti && r() < 0.7 && candidatosPasse.length
    ? ponderado(candidatosPasse, (x) => PESO_PASSE[x.setor] * (1 + (x.jogador.ast ?? 0) * 0.2), r).jogador : null;
  l.gols += 1;
  l.estat.finalizacoes += 1;
  l.estat.noAlvo += 1;
  l.marcadores.push({ min: rotuloMinuto(p), jogador: autor.id, penalti });
  const time = l.time.clube.nome;
  const a = nomeCurto(autor.nome);
  const texto = penalti
    ? `Pênalti para o ${time}! ${a} bate firme e marca.`
    : `GOL do ${time}! ${a} ${escolher(["finaliza cruzado e balança a rede", "bate de primeira, sem chance para o goleiro",
      "sobe mais que a zaga e cabeceia para o gol", "dribla o goleiro e empurra para a rede",
      "acerta um chute de fora da área no ângulo", "aproveita o rebote e marca", "completa o contra-ataque com categoria"], r)}${passe ? ` (passe de ${nomeCurto(passe.nome)})` : ""}.`;
  ev({ tipo: "gol", lado: i, jogador: autor.id, texto, placar: [p.lados[0].gols, p.lados[1].gols] });
}

function finalizacao(p, i, ev) {
  const r = p.aleatorio;
  const l = p.lados[i], adv = p.lados[1 - i];
  const autor = nomeCurto(sortearAutor(l, r).nome);
  l.estat.finalizacoes += 1;
  if (r() < 0.45) {
    l.estat.noAlvo += 1;
    const goleiro = nomeCurto(goleiroDe(adv).nome);
    ev({ tipo: "defesa", lado: i, texto: `${autor} ${escolher(["arrisca de longe", "cabeceia com perigo", "finaliza dentro da área", "bate colocado", "chuta forte de primeira"], r)} e ${goleiro} ${escolher(["faz grande defesa", "espalma para escanteio", "segura firme", "salva com o pé"], r)}.` });
  } else {
    ev({ tipo: "chance", lado: i, texto: `${autor} ${escolher(["manda por cima do gol.", "chuta para fora, com perigo.", "acerta a trave!", "perde chance clara cara a cara.", "cabeceia rente à trave."], r)}` });
  }
}

function cartao(p, i, direto, ev) {
  const r = p.aleatorio;
  const l = p.lados[i];
  const peso = { GOL: 0.2, DEF: 1.3, MEI: 1.2, ATA: 0.8 };
  const x = ponderado(l.emCampo, (y) => peso[y.setor] * (1 + (direto ? y.jogador.cv * 2 : y.jogador.ca * 0.3)), r);
  const j = x.jogador;
  const nome = nomeCurto(j.nome);
  if (!direto && !l.amarelos.has(j.id)) {
    l.amarelos.add(j.id);
    l.estat.amarelos += 1;
    ev({ tipo: "amarelo", lado: i, jogador: j.id, texto: `Amarelo para ${nome} (${l.time.clube.nome}) ${escolher(["por falta dura", "por reclamação", "por segurar o adversário", "por entrada atrasada", "por parar o contra-ataque"], r)}.` });
    return;
  }
  l.estat.vermelhos += 1;
  ev({ tipo: "vermelho", lado: i, jogador: j.id, texto: direto
    ? `Vermelho direto para ${nome} (${l.time.clube.nome})! O time fica com um a menos.`
    : `Segundo amarelo para ${nome}: expulso! O ${l.time.clube.nome} fica com um a menos.` });
  expulsar(p, i, x, ev);
}

function expulsar(p, i, x, ev) {
  const l = p.lados[i];
  l.expulsos.push(x.jogador.id);
  l.emCampo = l.emCampo.filter((y) => y !== x);
  if (x.setor === "GOL" && l.emCampo.length) {
    // Um jogador de linha vai para o gol até haver substituição.
    const improvisado = [...l.emCampo].sort((a, b) => ["ATA", "MEI", "DEF"].indexOf(a.setor) - ["ATA", "MEI", "DEF"].indexOf(b.setor))[0];
    improvisado.setor = "GOL";
    ev({ tipo: "info", lado: i, texto: `${nomeCurto(improvisado.jogador.nome)} vai improvisado para o gol.` });
  }
}

export function podeSubstituir(p, i) {
  const l = p.lados[i];
  return p.estado !== "fim" && l.subs < MAX_SUBSTITUICOES && l.banco.length > 0;
}

export function substituir(p, i, saiId, entraId) {
  const l = p.lados[i];
  if (!podeSubstituir(p, i)) return "Sem substituições disponíveis.";
  const x = l.emCampo.find((y) => y.jogador.id === saiId);
  if (!x) return "Esse jogador não está em campo.";
  if (!l.banco.includes(entraId)) return "Esse jogador não está no banco.";
  const entra = l.time.porId.get(entraId);
  const sai = x.jogador;
  x.jogador = entra;
  l.banco = l.banco.filter((id) => id !== entraId);
  l.jogaram.add(entraId);
  l.subs += 1;
  const evento = { min: rotuloMinuto(p), tipo: "sub", lado: i, texto: `Substituição no ${l.time.clube.nome}: sai ${nomeCurto(sai.nome)}, entra ${nomeCurto(entra.nome)}.` };
  p.eventos.push(evento);
  return null;
}

export function mudarPostura(p, i, postura) {
  const l = p.lados[i];
  if (l.postura === postura) return;
  l.postura = postura;
  p.eventos.push({ min: rotuloMinuto(p), tipo: "info", lado: i, texto: `O ${l.time.clube.nome} muda a postura: ${POSTURAS[postura].rotulo.toLowerCase()}.` });
}

// Troca a formação no meio do jogo: quem está em campo é redistribuído pelas vagas que o time
// ainda ocupa (com expulsão, uma vaga fica vazia), primeiro na posição de origem.
export function mudarFormacao(p, i, formacao) {
  const l = p.lados[i];
  if (l.formacao === formacao || !FORMACOES[formacao]) return;
  const setores = setoresDaFormacao(formacao);
  const vagas = l.emCampo.map((x) => x.vaga).sort((a, b) => a - b);
  const livres = new Set(l.emCampo.map((x) => x.jogador));
  const novo = [];
  const ordem = [...vagas].sort((a, b) => ["GOL", "ATA", "DEF", "MEI"].indexOf(setores[a]) - ["GOL", "ATA", "DEF", "MEI"].indexOf(setores[b]));
  for (const naturalPrimeiro of [true, false]) {
    for (const vaga of ordem) {
      if (novo.some((x) => x.vaga === vaga)) continue;
      const setor = setores[vaga];
      const j = [...livres].filter((x) => !naturalPrimeiro || x.setor === setor)
        .sort((a, b) => notaNaVaga(b, setor) - notaNaVaga(a, setor))[0];
      if (j) { novo.push({ jogador: j, setor, vaga }); livres.delete(j); }
    }
  }
  l.emCampo = novo.sort((a, b) => a.vaga - b.vaga);
  l.formacao = formacao;
  p.eventos.push({ min: rotuloMinuto(p), tipo: "info", lado: i, texto: `O ${l.time.clube.nome} muda para o ${formacao}.` });
}

// Troca dois jogadores em campo de lugar (não conta como substituição).
export function trocarPosicoes(p, i, idA, idB) {
  const l = p.lados[i];
  const a = l.emCampo.find((x) => x.jogador.id === idA);
  const b = l.emCampo.find((x) => x.jogador.id === idB);
  if (!a || !b || a === b) return;
  [a.jogador, b.jogador] = [b.jogador, a.jogador];
}

// Técnico adversário: muda a postura conforme o placar e troca quem está cansado.
function decidirIA(p, i, ev) {
  const l = p.lados[i], adv = p.lados[1 - i];
  const minuto = p.minuto;
  let postura = l.posturaInicial;
  if (p.periodo === 2 && minuto >= 70 && l.gols < adv.gols) postura = "ofensiva";
  else if (p.periodo === 2 && minuto >= 75 && l.gols > adv.gols) postura = "defensiva";
  if (postura !== l.postura) mudarPostura(p, i, postura);

  if (!podeSubstituir(p, i)) return;
  const goleiroImprovisado = l.emCampo.find((x) => x.setor === "GOL" && x.jogador.setor !== "GOL");
  const goleiroReserva = l.banco.find((id) => l.time.porId.get(id).setor === "GOL");
  if (goleiroImprovisado && goleiroReserva) {
    substituir(p, i, goleiroImprovisado.jogador.id, goleiroReserva);
    return;
  }
  if (p.periodo !== 2 || minuto < 55 || p.aleatorio() > 0.3) return;
  const valor = (j, setor) => notaNaVaga(j, setor) * fatorEnergia(l.energia[j.id]);
  const cansado = l.emCampo.filter((x) => x.setor !== "GOL" && l.energia[x.jogador.id] < 72)
    .sort((a, b) => l.energia[a.jogador.id] - l.energia[b.jogador.id])[0];
  if (!cansado) return;
  const reserva = l.banco.map((id) => l.time.porId.get(id)).filter((j) => j.setor !== "GOL")
    .sort((a, b) => valor(b, cansado.setor) - valor(a, cansado.setor))[0];
  if (reserva && valor(reserva, cansado.setor) > valor(cansado.jogador, cansado.setor)) {
    substituir(p, i, cansado.jogador.id, reserva.id);
  }
}

// --- Pênaltis ---------------------------------------------------------------
export const CANTOS = ["esquerda", "meio", "direita"];

export function criarDisputa(p, primeiro = 0) {
  const finalizacaoPenalti = (x) => x.jogador.nota + x.jogador.pen * 4 + { GOL: -25, DEF: 0, MEI: 3, ATA: 6 }[x.jogador.setor];
  return {
    cobradores: p.lados.map((l) => [...l.emCampo].sort((a, b) => finalizacaoPenalti(b) - finalizacaoPenalti(a)).map((x) => x.jogador)),
    goleiros: p.lados.map(goleiroDe),
    cobrancas: [[], []], vez: primeiro, fim: false, vencedor: null,
  };
}

export const golsDisputa = (dsp) => dsp.cobrancas.map((l) => l.filter((c) => c.gol).length);

export function proximoCobrador(dsp) {
  const lista = dsp.cobradores[dsp.vez];
  return lista[dsp.cobrancas[dsp.vez].length % lista.length];
}

export function cobrar(dsp, canto, mergulho, aleatorio = Math.random) {
  const i = dsp.vez;
  const batedor = proximoCobrador(dsp);
  const goleiro = dsp.goleiros[1 - i];
  const chanceFora = limitar(0.11 - (batedor.nota - 70) * 0.003, 0.03, 0.18);
  let resultado;
  if (aleatorio() < chanceFora) resultado = aleatorio() < 0.4 ? "trave" : "fora";
  else if (canto === mergulho) {
    const chanceDefesa = (canto === "meio" ? 0.72 : 0.58) + (goleiro.nota - batedor.nota) * 0.006;
    resultado = aleatorio() < chanceDefesa ? "defesa" : "gol";
  } else {
    resultado = aleatorio() < 0.03 ? "defesa" : "gol";
  }
  const cobranca = { jogador: batedor, goleiro, canto, mergulho, resultado, gol: resultado === "gol" };
  dsp.cobrancas[i].push(cobranca);
  dsp.vez = 1 - i;
  const [a, b] = dsp.cobrancas;
  const [ga, gb] = golsDisputa(dsp);
  if (a.length <= 5 && b.length <= 5) {
    if (ga + (5 - a.length) < gb || gb + (5 - b.length) < ga) dsp.fim = true;
  }
  if (!dsp.fim && a.length >= 5 && a.length === b.length && ga !== gb) dsp.fim = true;
  if (dsp.fim) dsp.vencedor = ga > gb ? 0 : 1;
  return cobranca;
}

export function cantoAleatorio(aleatorio = Math.random, goleiro = false) {
  const r = aleatorio();
  const meio = goleiro ? 0.16 : 0.2;
  return r < (1 - meio) / 2 ? "esquerda" : r < (1 + meio) / 2 ? "meio" : "direita";
}

// Simula um jogo inteiro sem interação (os outros jogos da fase e os testes).
export function simularPartida(casa, fora, aleatorio = Math.random) {
  const p = criarPartida({ ...casa, controlado: false }, { ...fora, controlado: false }, aleatorio);
  while (p.estado !== "fim") avancar(p);
  let disputa = null;
  if (p.lados[0].gols === p.lados[1].gols) {
    disputa = criarDisputa(p, aleatorio() < 0.5 ? 0 : 1);
    while (!disputa.fim) cobrar(disputa, cantoAleatorio(aleatorio), cantoAleatorio(aleatorio, true), aleatorio);
  }
  return { partida: p, disputa };
}

export function vencedorDe(p, disputa) {
  const [a, b] = p.lados.map((l) => l.gols);
  if (a !== b) return a > b ? 0 : 1;
  return disputa?.vencedor ?? null;
}
