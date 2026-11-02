// Minijogos: "Prancheta 2024", jogo de técnico com os elencos do Brasileirão 2024.
// Escolha um clube, monte a escalação e dispute um mata-mata de 8 times (quartas, semi e final).
// A campanha fica salva neste navegador entre uma fase e outra.
import { h, cabecalho, lerPreferencia, gravarPreferencia } from "../ui.js";
import { escudo } from "../imagens.js";
import { embaralhar, dataCurta } from "../dados.js";
import {
  prepararElencos, FORMACOES, POSTURAS, SETORES, setoresDaFormacao,
  escalarAutomatico, notaNaVaga, fatorEnergia,
} from "../tecnico/elenco.js";
import {
  criarPartida, avancar, previsao, substituir, mudarPostura, mudarFormacao, trocarPosicoes, podeSubstituir, MAX_SUBSTITUICOES,
  criarDisputa, cobrar, proximoCobrador, golsDisputa, cantoAleatorio, simularPartida, vencedorDe,
  rotuloMinuto, nomeCurto, CANTOS,
} from "../tecnico/motor.js";
import { coresDoTime, comVariaveis, botao, quadroTatico, campoDeJogo } from "../tecnico/quadro.js";

const CHAVE_CAMPANHA = "br24-prancheta-v1";
const CHAVE_TITULOS = "br24-prancheta-titulos";
const FASES = ["Quartas de final", "Semifinal", "Final"];
const NA_FASE = ["nas quartas de final", "na semifinal", "na final"];
const RECUPERACAO = 30;   // energia recuperada entre uma fase e outra

let times = null;
let dados = null;

export function render(main, d) {
  carregarEstilo();
  if (dados !== d) { dados = d; times = prepararElencos(d); }
  main.append(cabecalho("Prancheta 2024",
    "Jogo de técnico: escolha um clube do Brasileirão 2024, escale o time e dispute um mata-mata das quartas à final. A força de cada elenco vem do desempenho real na temporada."));
  const palco = h("div", { class: "pr" });
  main.append(palco);
  const c = lerPreferencia(CHAVE_CAMPANHA, null);
  if (c?.v === 1 && times.has(c.clube)) abrirCampanha(palco, c);
  else telaInicio(palco);
}

function carregarEstilo() {
  if (document.querySelector("link[data-prancheta]")) return;
  document.head.append(h("link", { rel: "stylesheet", href: "css/jogo_tecnico.css", "data-prancheta": "" }));
}

// replaceChildren sem os filhos nulos (partes opcionais da tela).
const trocar = (el, ...filhos) => el.replaceChildren(...filhos.flat().filter((f) => f !== null && f !== undefined && f !== false));
const salvar = (c) => gravarPreferencia(CHAVE_CAMPANHA, c);
const descartar = () => gravarPreferencia(CHAVE_CAMPANHA, null);
const time = (id) => times.get(id);

const nEstrelas = (forca) => (forca >= 85 ? 5 : forca >= 79 ? 4 : forca >= 73 ? 3 : forca >= 68 ? 2 : 1);
const DIFICULDADE = { 5: "Favorito ao título", 4: "Candidato", 3: "Azarão", 2: "Desafio", 1: "Missão quase impossível" };

function estrelas(forca) {
  const n = nEstrelas(forca);
  return h("span", { class: "pr-estrelas", "aria-label": `${n} de 5 estrelas`, title: `Força ${forca}` },
    "★".repeat(n), h("span", {}, "★".repeat(5 - n)));
}

// --- Início -------------------------------------------------------------------
function telaInicio(palco) {
  let modo = lerPreferencia("br24-prancheta-modo", "elite");
  const titulos = lerPreferencia(CHAVE_TITULOS, {});
  const lista = [...times.values()].sort((a, b) => b.forca - a.forca || a.posicao - b.posicao);
  const abas = h("div", { class: "abas pr-sem-margem", role: "group", "aria-label": "Rivais do torneio" });
  const explicacao = h("p", { class: "mudo pequeno pr-sem-margem" });
  const desenharAbas = () => {
    abas.replaceChildren(
      h("button", { type: "button", "aria-pressed": String(modo === "elite"), onclick: () => { modo = "elite"; desenharAbas(); } }, "Elite"),
      h("button", { type: "button", "aria-pressed": String(modo === "sorteio"), onclick: () => { modo = "sorteio"; desenharAbas(); } }, "Sorteio"));
    explicacao.textContent = modo === "elite"
      ? "Seu clube enfrenta os 7 melhores colocados de 2024. Quanto mais fraco o seu time, maior o desafio."
      : "Os 7 rivais são sorteados entre os outros 19 clubes.";
    gravarPreferencia("br24-prancheta-modo", modo);
  };
  desenharAbas();

  const salaTrofeus = Object.entries(titulos).filter(([id, n]) => n > 0 && times.has(id)).sort((a, b) => b[1] - a[1]);
  trocar(palco,
    h("section", { class: "cartao pr-intro" },
      h("div", {},
        h("h2", {}, "Como funciona"),
        h("ol", { class: "pr-passos" },
          h("li", {}, h("strong", {}, "Escolha o clube. "), "As estrelas mostram a força do elenco, calculada com pontos, gols e destaques reais de 2024."),
          h("li", {}, h("strong", {}, "Monte a escalação. "), "Formação, postura e os 11 titulares. Jogador fora de posição rende menos."),
          h("li", {}, h("strong", {}, "Comande os jogos. "), "Partidas minuto a minuto com substituições, cartões e cansaço. Empate vai para os pênaltis, e você escolhe o canto."))),
      h("div", { class: "pr-intro-modo" }, h("span", { class: "kpi-rotulo" }, "Rivais"), abas, explicacao)),
    salaTrofeus.length ? h("section", { class: "cartao pr-trofeus" }, h("h2", {}, "🏆 Sala de troféus"),
      h("div", { class: "pr-trofeus-lista" }, salaTrofeus.map(([id, n]) =>
        h("span", { class: "pr-trofeu" }, escudo(time(id).clube), h("span", {}, time(id).clube.nome), h("strong", {}, `${n}×`))))) : null,
    h("h2", { class: "pr-titulo-secao" }, "Escolha o seu clube"),
    h("div", { class: "pr-clubes" }, lista.map((t) => comVariaveis(h("button", {
      class: "cartao pr-clube", type: "button",
      onclick: () => iniciarCampanha(palco, t.id, modo),
    },
    escudo(t.clube, "escudo-lg"),
    h("span", { class: "pr-clube-info" },
      h("strong", {}, t.clube.nome),
      estrelas(t.forca),
      h("span", { class: "mudo pequeno" }, `${t.posicao}º em 2024 · ${t.pts} pts`),
      h("span", { class: "pr-dificuldade pequeno" }, DIFICULDADE[nEstrelas(t.forca)])),
    h("span", { class: "pr-forca", title: "Força do elenco (média dos 11 titulares)" }, t.forca)), { "--cor-clube": t.clube.cor1 }))));
}

// --- Campanha -----------------------------------------------------------------
function iniciarCampanha(palco, clube, modo) {
  const outros = [...times.values()].filter((t) => t.id !== clube);
  const rivais = modo === "sorteio" ? embaralhar(outros).slice(0, 7) : outros.sort((a, b) => a.posicao - b.posicao).slice(0, 7);
  // Cabeças de chave pela posição real em 2024: 1x8, 4x5, 2x7, 3x6.
  const s = [time(clube), ...rivais].sort((a, b) => a.posicao - b.posicao).map((t) => t.id);
  const t = time(clube);
  const c = {
    v: 1, clube, modo, chave: [s[0], s[7], s[3], s[4], s[1], s[6], s[2], s[5]], fase: 0,
    resultados: [[], [], []], energia: {}, suspensos: [], artilharia: {}, status: "jogando",
    tatica: { formacao: t.formacao, postura: "equilibrada", titulares: escalarAutomatico(t, t.formacao) },
  };
  salvar(c);
  abrirCampanha(palco, c);
}

function abrirCampanha(palco, c) {
  if (c.status !== "jogando") telaFim(palco, c);
  else telaVestiario(palco, c);
}

function confrontos(c, fase) {
  const ids = fase === 0 ? c.chave : c.resultados[fase - 1].map((r) => r.vencedor);
  const pares = [];
  for (let i = 0; i < ids.length; i += 2) pares.push([ids[i], ids[i + 1]]);
  return pares;
}

function adversarioAtual(c) {
  const par = confrontos(c, c.fase).find((x) => x.includes(c.clube));
  return par[0] === c.clube ? par[1] : par[0];
}

const energiaDe = (c, id) => c.energia[id] ?? 100;
const valorNaVaga = (c, j, setor) => notaNaVaga(j, setor) * fatorEnergia(energiaDe(c, j.id));

// Tira suspensos, repetidos e ids inválidos da escalação salva e completa as vagas.
function validarEscalacao(c) {
  const t = time(c.clube);
  const setores = setoresDaFormacao(c.tatica.formacao);
  const suspensos = new Set(c.suspensos);
  const vistos = new Set();
  const ids = setores.map((_, i) => {
    const id = c.tatica.titulares[i];
    if (!id || !t.porId.has(id) || suspensos.has(id) || vistos.has(id)) return null;
    vistos.add(id);
    return id;
  });
  setores.forEach((setor, i) => {
    if (ids[i]) return;
    const j = t.jogadores.filter((x) => !vistos.has(x.id) && !suspensos.has(x.id))
      .sort((a, b) => valorNaVaga(c, b, setor) - valorNaVaga(c, a, setor))[0];
    if (j) { ids[i] = j.id; vistos.add(j.id); }
  });
  c.tatica.titulares = ids;
}

// Ao trocar de formação, mantém os mesmos 11 e redistribui pelas novas vagas.
function reorganizar(c, formacao) {
  const t = time(c.clube);
  const livres = new Set(c.tatica.titulares.map((id) => t.porId.get(id)).filter(Boolean));
  const setores = setoresDaFormacao(formacao);
  const novos = Array(11).fill(null);
  setores.forEach((setor, i) => {
    const j = [...livres].filter((x) => x.setor === setor).sort((a, b) => b.nota - a.nota)[0];
    if (j) { novos[i] = j.id; livres.delete(j); }
  });
  setores.forEach((setor, i) => {
    if (novos[i]) return;
    const j = [...livres].sort((a, b) => notaNaVaga(b, setor) - notaNaVaga(a, setor))[0];
    if (j) { novos[i] = j.id; livres.delete(j); }
  });
  c.tatica = { ...c.tatica, formacao, titulares: novos };
}

function configUsuario(c) {
  return {
    time: time(c.clube), formacao: c.tatica.formacao, postura: c.tatica.postura, titulares: c.tatica.titulares,
    energia: c.energia, indisponiveis: new Set(c.suspensos), controlado: true,
  };
}

// Técnico adversário: formação mais usada pelo clube em 2024; recua contra time mais forte.
function configIA(c, id, forcaRival) {
  const t = time(id);
  const indisponiveis = new Set(c.suspensos);
  const postura = t.forca <= forcaRival - 6 ? "defensiva" : t.forca >= forcaRival + 6 ? "ofensiva" : "equilibrada";
  return {
    time: t, formacao: t.formacao, postura, energia: c.energia, indisponiveis,
    titulares: escalarAutomatico(t, t.formacao, { energia: c.energia, indisponiveis }),
  };
}

// --- Vestiário (escalação) --------------------------------------------------------
function chips(rotulo, opcoes, atual, aoEscolher) {
  return h("div", { class: "pr-chips", role: "group", "aria-label": rotulo }, opcoes.map(([valor, texto, titulo]) =>
    h("button", { type: "button", "aria-pressed": String(valor === atual), title: titulo || null, onclick: () => aoEscolher(valor) }, texto)));
}

function telaVestiario(palco, c) {
  validarEscalacao(c);
  salvar(c);
  const t = time(c.clube);
  const adv = time(adversarioAtual(c));
  const cores = coresDoTime(t.clube);
  const coresAdv = coresDoTime(adv.clube, t.clube);
  const suspensos = new Set(c.suspensos);
  const comparacao = h("div");
  const taticas = h("div", { class: "pr-taticas" });

  const quadro = quadroTatico({
    cores,
    formacao: () => c.tatica.formacao,
    vagas: () => c.tatica.titulares.map((id) => ({ jogador: t.porId.get(id) || null })),
    banco: () => t.jogadores.filter((j) => !c.tatica.titulares.includes(j.id)).map((j) => ({
      jogador: j, bloqueado: suspensos.has(j.id), motivo: suspensos.has(j.id) ? "suspenso por expulsão" : null,
    })),
    nota: (j, setor) => notaNaVaga(j, setor),
    energia: (id) => energiaDe(c, id),
    aoTrocar: (a, b) => {
      const ids = c.tatica.titulares;
      if (a.vaga !== undefined && b.vaga !== undefined) [ids[a.vaga], ids[b.vaga]] = [ids[b.vaga], ids[a.vaga]];
      else if (a.banco !== undefined && b.banco !== undefined) return "Os dois estão no banco: escolha um titular e um reserva.";
      else ids[a.vaga ?? b.vaga] = a.banco ?? b.banco;
      atualizar();
      return "";
    },
  });

  function desenharTaticas() {
    taticas.replaceChildren(
      h("div", {}, h("span", { class: "kpi-rotulo" }, "Formação"),
        chips("Formação", Object.entries(FORMACOES).map(([nome, f]) => [nome, nome, f.estilo]), c.tatica.formacao, (nome) => {
          reorganizar(c, nome);
          quadro.limpar();
          atualizar();
        }),
        h("span", { class: "mudo pequeno" }, FORMACOES[c.tatica.formacao].estilo)),
      h("div", {}, h("span", { class: "kpi-rotulo" }, "Postura"),
        chips("Postura", Object.entries(POSTURAS).map(([id, x]) => [id, x.rotulo]), c.tatica.postura, (id) => {
          c.tatica.postura = id;
          atualizar();
        }),
        h("span", { class: "mudo pequeno" }, { defensiva: "Sofre menos gols, mas ataca menos.", equilibrada: "Nem retranca, nem abafa.", ofensiva: "Mais chances para os dois lados e mais cansaço." }[c.tatica.postura])));
  }

  function desenharComparacao() {
    const pr = previsao(configUsuario(c), configIA(c, adv.id, t.forca));
    const [fa, fb] = pr.forcas;
    const linhas = [["Ataque", "ataque"], ["Meio-campo", "meio"], ["Defesa", "defesa"], ["Goleiro", "GOL"]];
    const largura = (v) => `${Math.max(4, Math.min(100, (v - 40) * 1.8))}%`;
    comparacao.replaceChildren(
      h("div", { class: "pr-comparacao" },
        h("div", { class: "pr-comp-topo mudo pequeno" }, h("span", {}, t.clube.nome), h("span", {}, adv.clube.nome)),
        ...linhas.map(([rotulo, k]) => {
          const a = Math.round(fa[k]), b = Math.round(fb[k]);
          return h("div", { class: "pr-comp-linha" },
            h("strong", { class: a > b ? "melhor" : "" }, a),
            h("div", { class: "pr-comp-barras" },
              h("div", { class: "pr-comp-barra esq" }, h("i", { style: { width: largura(a), background: cores.fundo === "#f4f4f2" ? "#898781" : cores.fundo } })),
              h("span", { class: "mudo pequeno" }, rotulo),
              h("div", { class: "pr-comp-barra dir" }, h("i", { style: { width: largura(b), background: coresAdv.fundo === "#f4f4f2" ? "#898781" : coresAdv.fundo } }))),
            h("strong", { class: b > a ? "melhor" : "" }, b));
        })),
      h("div", { class: "pr-previsao" },
        h("span", { class: "kpi-rotulo" }, "Chances em 90 minutos (estimativa)"),
        h("div", { class: "pr-tripla" },
          h("div", { style: { flex: pr.vitoria, background: "var(--bom)" }, title: "Vitória" }, `${Math.round(100 * pr.vitoria)}%`),
          h("div", { style: { flex: pr.empate, background: "#898781" }, title: "Empate" }, `${Math.round(100 * pr.empate)}%`),
          h("div", { style: { flex: pr.derrota, background: "var(--ruim)" }, title: "Derrota" }, `${Math.round(100 * pr.derrota)}%`)),
        h("div", { class: "pr-legenda-previsao mudo pequeno" }, h("span", {}, "Vitória"), h("span", {}, "Empate (pênaltis)"), h("span", {}, "Derrota"))));
  }

  function atualizar() {
    salvar(c);
    quadro.desenhar();
    desenharTaticas();
    desenharComparacao();
  }

  const confrontosReais = dados.partidas.filter((p) => (p.m === t.id && p.v === adv.id) || (p.m === adv.id && p.v === t.id));
  palco.replaceChildren(
    barraCampanha(palco, c),
    h("div", { class: "pr-vestiario" },
      comVariaveis(h("section", { class: "cartao pr-escalacao" },
        h("div", { class: "pr-cab-cartao" }, h("h2", {}, escudo(t.clube), `Escalação do ${t.clube.nome}`),
          h("button", { class: "botao", type: "button", onclick: () => {
            c.tatica.titulares = escalarAutomatico(t, c.tatica.formacao, { energia: c.energia, indisponiveis: suspensos });
            quadro.limpar();
            atualizar();
          } }, "Escalar automaticamente")),
        taticas,
        quadro.el), { "--cor-clube": cores.fundo }),
      h("aside", { class: "pr-lateral" },
        h("button", { class: "botao botao-primario pr-botao-grande", type: "button", onclick: () => telaPartida(palco, c) }, "Começar a partida ▶"),
        h("section", { class: "cartao pr-adversario" },
          h("span", { class: "kpi-rotulo" }, `${FASES[c.fase]} · adversário`),
          h("div", { class: "pr-adv-topo" }, escudo(adv.clube, "escudo-lg"),
            h("div", {}, h("strong", { class: "pr-grande" }, adv.clube.nome), h("div", {}, estrelas(adv.forca)),
              h("div", { class: "mudo pequeno" }, `${adv.posicao}º em 2024 · técnico ${adv.tecnico} · ${adv.formacao}`))),
          h("div", { class: "pr-destaques" }, adv.jogadores.slice().sort((a, b) => b.nota - a.nota).slice(0, 3).map((j) =>
            h("div", { class: "pr-destaque" }, botao(coresAdv, j.nota), h("span", { class: "pequeno" }, nomeCurto(j.nome)),
              h("span", { class: "mudo pequeno" }, SETORES[j.setor])))),
          confrontosReais.length ? h("p", { class: "mudo pequeno pr-sem-margem" }, h("strong", {}, "No Brasileirão 2024: "),
            confrontosReais.map((p) => `${time(p.m).clube.nome} ${p.gm} x ${p.gv} ${time(p.v).clube.nome} (${dataCurta(p.data)})`).join(" · ")) : null),
        h("section", { class: "cartao" }, h("h2", {}, "Comparação"), comparacao),
        h("section", { class: "cartao" }, h("h2", {}, "Chaveamento"), chaveamento(c)))));
  atualizar();
}

function barraCampanha(palco, c) {
  const t = time(c.clube);
  return h("div", { class: "pr-barra" },
    h("div", { class: "pr-barra-fases" }, FASES.map((f, i) =>
      h("span", { class: c.status === "campeao" || i < c.fase ? "feita" : i === c.fase ? "atual" : "" }, f))),
    h("span", { class: "mudo pequeno pr-barra-clube" }, escudo(t.clube), `${t.clube.nome} · modo ${c.modo === "elite" ? "Elite" : "Sorteio"}`),
    h("button", { class: "botao", type: "button", onclick: () => {
      if (confirm("Abandonar esta campanha e escolher outro clube?")) { descartar(); telaInicio(palco); }
    } }, "Abandonar"));
}

// --- Partida -----------------------------------------------------------------------
const VELOCIDADES = [["1x", 650], ["2x", 300]];
const ICONES = { gol: "⚽", defesa: "🧤", chance: "💨", amarelo: "🟨", vermelho: "🟥", sub: "🔁", apito: "📣", info: "📋" };

function telaPartida(palco, c) {
  const t = time(c.clube);
  const adv = time(adversarioAtual(c));
  const p = criarPartida(configUsuario(c), configIA(c, adv.id, t.forca));
  const eu = p.lados[0], ele = p.lados[1];
  const cores = [coresDoTime(t.clube), coresDoTime(adv.clube, t.clube)];
  let velocidade = Math.min(1, lerPreferencia("br24-prancheta-vel", 0));
  let timer = null;
  let posseAnterior = 0;

  const campo = campoDeJogo(p, cores);
  const placar = h("section", { class: "pr-placar" });
  const narracao = h("ol", { class: "pr-narracao", "aria-live": "polite" });
  const todos = h("ol", { class: "pr-lances" });
  const estat = h("div", { class: "pr-estat-compacta" });
  const controles = h("div", { class: "pr-controles" });
  const faixa = h("div", { class: "pr-faixa", role: "status" });

  const rodando = () => timer !== null;
  function iniciar() {
    if (p.estado === "fim" || rodando()) return;
    timer = setInterval(passo, VELOCIDADES[velocidade][1]);
    desenhar();
  }
  function pausar() {
    clearInterval(timer);
    timer = null;
    desenhar();
  }

  function passo() {
    if (!palco.isConnected) { clearInterval(timer); timer = null; return; }
    const novos = avancar(p);
    const posseEu = eu.estat.posse - posseAnterior;
    posseAnterior = eu.estat.posse;
    campo.animar(novos, posseEu, VELOCIDADES[velocidade][1]);
    novos.forEach(adicionarLance);
    if (novos.some((e) => e.tipo === "gol")) {
      placar.classList.remove("pr-golaco");
      void placar.offsetWidth;
      placar.classList.add("pr-golaco");
    }
    // Pausa no intervalo, no fim e quando o seu time tem alguém expulso.
    if (p.estado === "intervalo" || p.estado === "fim" || novos.some((e) => e.tipo === "vermelho" && e.lado === 0)) pausar();
    else desenhar();
  }

  function linhaLance(e) {
    return h("li", { class: `pr-lance t-${e.tipo}${e.lado === 0 ? " meu" : e.lado === 1 ? " deles" : ""}` },
      h("span", { class: "pr-lance-min" }, e.min), h("span", { "aria-hidden": "true" }, ICONES[e.tipo] || "•"), h("span", {}, e.texto));
  }
  function adicionarLance(e) { todos.prepend(linhaLance(e)); }

  function soResultado() {
    clearInterval(timer);
    timer = null;
    while (p.estado !== "fim") avancar(p).forEach(adicionarLance);
    campo.animar([], 0.5, 300);
    desenhar();
  }

  function desenhar() {
    const lado = (l, i) => h("div", { class: `pr-placar-lado${i ? " dir" : ""}` },
      escudo(l.time.clube, "escudo-lg"),
      h("div", {}, h("strong", {}, l.time.clube.nome),
        h("span", { class: "pr-placar-gols mudo pequeno" }, l.marcadores.map((m) => `${nomeCurto(l.time.porId.get(m.jogador).nome)} ${m.min}${m.penalti ? " (pên.)" : ""}`).join(", ")),
        l.expulsos.length ? h("span", { class: "pequeno", title: "Expulsões" }, "🟥".repeat(l.expulsos.length)) : null));
    placar.style.setProperty("--cor-a", cores[0].fundo);
    placar.style.setProperty("--cor-b", cores[1].fundo);
    placar.replaceChildren(
      lado(eu, 0),
      h("div", { class: "pr-placar-centro" },
        h("span", { class: "pr-placar-numeros" }, `${eu.gols} x ${ele.gols}`),
        h("span", { class: "pr-relogio" }, p.estado === "intervalo" ? "Intervalo" : p.estado === "fim" ? "Fim de jogo" : p.estado === "pre" ? FASES[c.fase] : rotuloMinuto(p))),
      lado(ele, 1));

    const recentes = p.eventos.slice(-3).reverse();
    narracao.replaceChildren(...(recentes.length ? recentes.map((e, i) => {
      const li = linhaLance(e);
      if (i === 0) li.classList.add("ultimo");
      return li;
    }) : [h("li", { class: "pr-lance" }, h("span", {}), h("span", {}), h("span", { class: "mudo" }, "Toque em Começar para a bola rolar."))]));

    const total = eu.estat.posse + ele.estat.posse;
    const posse = total ? Math.round((100 * eu.estat.posse) / total) : 50;
    const dado = (rotulo, a, b) => h("div", { class: "pr-dado" }, h("strong", {}, a), h("span", { class: "mudo pequeno" }, rotulo), h("strong", {}, b));
    estat.replaceChildren(
      h("div", { class: "pr-dado posse" }, h("span", { class: "mudo pequeno" }, "Posse"),
        h("div", { class: "pr-tripla" },
          h("div", { style: { flex: posse || 1, background: cores[0].fundo, color: cores[0].texto } }, `${posse}%`),
          h("div", { style: { flex: 100 - posse || 1, background: cores[1].fundo, color: cores[1].texto } }, `${100 - posse}%`))),
      dado("Finalizações", eu.estat.finalizacoes, ele.estat.finalizacoes),
      dado("No alvo", eu.estat.noAlvo, ele.estat.noAlvo),
      dado("Cartões", eu.estat.amarelos + eu.estat.vermelhos, ele.estat.amarelos + ele.estat.vermelhos));

    const fim = p.estado === "fim";
    faixa.hidden = true;
    if (p.estado === "intervalo") mostrarFaixa("Intervalo. Ajuste o time e volte para o segundo tempo.");
    else if (fim) {
      mostrarFaixa(eu.gols === ele.gols ? "Empate no tempo normal: a vaga será decidida nos pênaltis."
        : eu.gols > ele.gols ? "Vitória! Você avançou de fase." : "Derrota. Fim da linha neste torneio.");
    } else if (!rodando() && p.estado === "jogo" && p.eventos.at(-1)?.tipo === "vermelho" && p.eventos.at(-1)?.lado === 0) {
      mostrarFaixa("Seu time ficou com um a menos. Veja se precisa mexer no time.");
    }

    if (fim) {
      controles.replaceChildren(h("button", { class: "botao botao-primario pr-botao-grande", type: "button", onclick: () => concluirPartida(palco, c, p) },
        eu.gols === ele.gols ? "Ir para os pênaltis ▶" : "Continuar ▶"));
      return;
    }
    controles.replaceChildren(
      h("button", { class: "botao botao-primario pr-botao-grande", type: "button", onclick: () => (rodando() ? pausar() : iniciar()) },
        rodando() ? "⏸ Pausar" : p.estado === "pre" ? "▶ Começar" : p.estado === "intervalo" ? "▶ Segundo tempo" : "▶ Continuar"),
      h("button", { class: "botao pr-botao-grande", type: "button", onclick: abrirPrancheta },
        `📋 Pausar e mexer no time`, h("span", { class: "pr-contador", title: "Substituições restantes" }, MAX_SUBSTITUICOES - eu.subs)),
      chips("Velocidade", VELOCIDADES.map(([r], i) => [i, r]), velocidade, (i) => {
        velocidade = i;
        gravarPreferencia("br24-prancheta-vel", i);
        if (rodando()) { clearInterval(timer); timer = setInterval(passo, VELOCIDADES[velocidade][1]); }
        desenhar();
      }),
      h("button", { class: "botao", type: "button", onclick: soResultado }, "⏭ Só o resultado"));
  }

  function mostrarFaixa(texto) {
    faixa.hidden = false;
    faixa.textContent = texto;
  }

  // Prancheta durante o jogo: substituições, troca de posições, formação e postura.
  function abrirPrancheta() {
    if (rodando()) pausar();
    let pendente = null;
    const dialogo = h("dialog", { class: "pr-dialogo", "aria-label": "Mexer no time" });
    const topo = h("div", { class: "pr-dialogo-topo" });
    const taticas = h("div", { class: "pr-taticas" });
    const fechar = () => dialogo.close();

    const quadro = quadroTatico({
      cores: cores[0],
      formacao: () => eu.formacao,
      vagas: () => {
        const vagas = Array.from({ length: 11 }, () => ({ ausente: true }));
        for (const x of eu.emCampo) vagas[x.vaga] = { jogador: x.jogador, marca: eu.amarelos.has(x.jogador.id) ? " 🟨" : "" };
        return vagas;
      },
      banco: () => eu.banco.map((id) => ({
        jogador: eu.time.porId.get(id), bloqueado: !podeSubstituir(p, 0), motivo: "sem substituições restantes",
      })),
      nota: (j, setor) => notaNaVaga(j, setor) * fatorEnergia(eu.energia[j.id]),
      energia: (id) => eu.energia[id],
      aoTrocar: (a, b) => {
        const emCampo = (alvo) => eu.emCampo.find((x) => x.vaga === alvo.vaga);
        if (a.vaga !== undefined && b.vaga !== undefined) {
          trocarPosicoes(p, 0, emCampo(a).jogador.id, emCampo(b).jogador.id);
          campo.sincronizar();
          pendente = null;
          return "Posições trocadas.";
        }
        if (a.banco !== undefined && b.banco !== undefined) return "Os dois estão no banco: escolha quem sai do campo.";
        pendente = { sai: emCampo(a.vaga !== undefined ? a : b).jogador, entra: eu.time.porId.get(a.banco ?? b.banco) };
        return "";
      },
      rodape: () => {
        const improvisado = eu.emCampo.find((x) => x.setor === "GOL" && x.jogador.setor !== "GOL");
        if (pendente) {
          const caixa = h("div", { class: "pr-confirmar" },
            h("p", { class: "pr-sem-margem" }, "Sai ", h("strong", {}, pendente.sai.nome), ", entra ", h("strong", {}, pendente.entra.nome), "."),
            h("div", { class: "pr-confirmar-botoes" },
              h("button", { class: "botao botao-primario", type: "button", onclick: () => {
                const erro = substituir(p, 0, pendente.sai.id, pendente.entra.id);
                pendente = null;
                if (!erro) adicionarLance(p.eventos.at(-1));
                campo.sincronizar();
                desenharTudo();
              } }, "Confirmar substituição"),
              h("button", { class: "botao", type: "button", onclick: () => { pendente = null; quadro.desenhar(); } }, "Cancelar")));
          // No celular o banco fica abaixo: traz a confirmação para a vista.
          requestAnimationFrame(() => caixa.scrollIntoView({ block: "nearest", behavior: "smooth" }));
          return caixa;
        }
        return improvisado ? h("p", { class: "aviso pr-sem-margem" }, `${nomeCurto(improvisado.jogador.nome)} está improvisado no gol: troque por um goleiro do banco.`) : null;
      },
    });

    function desenharTudo() {
      topo.replaceChildren(
        h("div", {}, h("h2", { class: "pr-sem-margem" }, "Mexer no time"),
          h("span", { class: "mudo pequeno" }, `${p.estado === "intervalo" ? "Intervalo" : rotuloMinuto(p)} · ${eu.gols} x ${ele.gols} · ${MAX_SUBSTITUICOES - eu.subs} substituições restantes`)),
        h("button", { class: "botao botao-primario", type: "button", onclick: () => { fechar(); iniciar(); } }, "▶ Voltar ao jogo"));
      taticas.replaceChildren(
        h("div", {}, h("span", { class: "kpi-rotulo" }, "Formação"),
          chips("Formação", Object.keys(FORMACOES).map((n) => [n, n, FORMACOES[n].estilo]), eu.formacao, (n) => {
            mudarFormacao(p, 0, n);
            adicionarLance(p.eventos.at(-1));
            campo.sincronizar();
            quadro.limpar();
            desenharTudo();
          })),
        h("div", {}, h("span", { class: "kpi-rotulo" }, "Postura"),
          chips("Postura", Object.entries(POSTURAS).map(([id, x]) => [id, x.rotulo]), eu.postura, (id) => {
            mudarPostura(p, 0, id);
            c.tatica.postura = id;
            adicionarLance(p.eventos.at(-1));
            desenharTudo();
          })));
      quadro.desenhar();
      desenhar();
    }

    dialogo.append(topo, taticas, quadro.el);
    dialogo.addEventListener("close", () => dialogo.remove());
    dialogo.addEventListener("click", (e) => { if (e.target === dialogo) fechar(); });
    document.body.append(dialogo);
    desenharTudo();
    dialogo.showModal();
  }

  palco.replaceChildren(
    barraCampanha(palco, c),
    h("section", { class: "cartao pr-partida" },
      placar,
      h("div", { class: "pr-gramado-moldura" }, campo.el),
      narracao,
      estat),
    faixa, controles,
    h("details", { class: "cartao pr-todos" }, h("summary", {}, "Todos os lances"), todos));
  desenhar();
}

// --- Pênaltis ----------------------------------------------------------------------
const NOME_CANTO = { esquerda: "Esquerda", meio: "Meio", direita: "Direita" };
const CANTO_FRASE = { esquerda: "no canto esquerdo", meio: "no meio do gol", direita: "no canto direito" };
const MERGULHO_FRASE = { esquerda: "para a esquerda", meio: "ficou no meio", direita: "para a direita" };

function telaPenaltis(palco, c, p, aoTerminar) {
  const dsp = criarDisputa(p, Math.random() < 0.5 ? 0 : 1);
  const [eu, ele] = p.lados;
  let mensagem = null;
  let travado = false;
  const area = h("section", { class: "cartao pr-penaltis" });

  function marcas(i) {
    const cob = dsp.cobrancas[i];
    const n = Math.max(5, cob.length, dsp.cobrancas[1 - i].length);
    return h("div", { class: "pr-pen-marcas" }, Array.from({ length: n }, (_, k) => h("i", {
      class: k < cob.length ? (cob[k].gol ? "gol" : "perdeu") : "",
      title: k < cob.length ? `${cob[k].jogador.nome}: ${cob[k].gol ? "gol" : cob[k].resultado}` : "A cobrar",
    })));
  }

  function escolher(canto) {
    if (travado) return;
    travado = true;
    const nossa = dsp.vez === 0;
    const r = cobrar(dsp, nossa ? canto : cantoAleatorio(), nossa ? cantoAleatorio(Math.random, true) : canto);
    const batedor = nomeCurto(r.jogador.nome);
    const textos = {
      gol: `GOL! ${batedor} bateu ${CANTO_FRASE[r.canto]} e o goleiro ${r.mergulho === "meio" ? "ficou no meio" : `pulou ${MERGULHO_FRASE[r.mergulho]}`}.`,
      defesa: `DEFENDEU! ${nomeCurto(r.goleiro.nome)} adivinhou: a bola foi ${CANTO_FRASE[r.canto]}.`,
      fora: `PRA FORA! ${batedor} mandou por cima do gol.`,
      trave: `NA TRAVE! ${batedor} bateu ${CANTO_FRASE[r.canto]} e a bola explodiu no poste.`,
    };
    mensagem = { texto: textos[r.resultado], bom: r.gol === nossa, canto: r.canto, mergulho: r.mergulho, nossa, cobranca: r };
    desenhar();
    setTimeout(() => { travado = false; mensagem = null; if (area.isConnected) desenhar(); }, 1600);
  }

  function desenhar() {
    const [ga, gb] = golsDisputa(dsp);
    // Enquanto o resultado aparece, o cartaz continua mostrando quem acabou de bater.
    const nossa = mensagem ? mensagem.nossa : dsp.vez === 0;
    const batedor = mensagem ? mensagem.cobranca.jogador : proximoCobrador(dsp);
    const goleiro = mensagem ? mensagem.cobranca.goleiro : dsp.goleiros[nossa ? 1 : 0];
    const fim = dsp.fim && !mensagem;
    area.replaceChildren(
      h("h2", {}, "Disputa de pênaltis"),
      h("div", { class: "pr-pen-placar" },
        h("div", {}, h("div", { class: "clube-inline" }, escudo(eu.time.clube), h("strong", {}, eu.time.clube.nome)), marcas(0)),
        h("span", { class: "pr-placar-numeros" }, `${ga} x ${gb}`),
        h("div", { class: "dir" }, h("div", { class: "clube-inline" }, h("strong", {}, ele.time.clube.nome), escudo(ele.time.clube)), marcas(1))),
      fim
        ? h("div", { class: "pr-pen-fim" },
          h("p", { class: "pr-grande" }, dsp.vencedor === 0 ? "🎉 Classificado nos pênaltis!" : "😞 Eliminado nos pênaltis."),
          h("button", { class: "botao botao-primario pr-botao-grande", type: "button", onclick: () => aoTerminar(dsp) }, "Continuar ▶"))
        : h("div", {},
          h("div", { class: "pr-pen-cobrador" }, botao(coresDoTime((nossa ? eu : ele).time.clube, (nossa ? ele : eu).time.clube), batedor.nota, { classe: "grande" }),
            h("div", {}, h("strong", {}, nossa ? `Sua cobrança: ${batedor.nome}` : `Cobra pelo ${ele.time.clube.nome}: ${batedor.nome}`),
              h("p", { class: "mudo pequeno pr-sem-margem" }, nossa ? `No gol adversário: ${goleiro.nome}.` : `Seu goleiro: ${goleiro.nome}.`))),
          h("div", { class: `pr-gol${mensagem ? (mensagem.bom ? " bom" : " ruim") : ""}` },
            CANTOS.map((canto) => h("button", {
              type: "button", disabled: travado, onclick: () => escolher(canto),
              class: `pr-canto${mensagem?.canto === canto ? " bola" : ""}${mensagem?.mergulho === canto ? " goleiro" : ""}`,
              "aria-label": nossa ? `Bater ${CANTO_FRASE[canto]}` : `Goleiro pula: ${NOME_CANTO[canto]}`,
            }, h("span", {}, NOME_CANTO[canto])))),
          h("p", { class: "pr-pen-msg", role: "status" }, mensagem ? mensagem.texto
            : nossa ? "Escolha onde bater." : "Escolha para onde o seu goleiro pula.")));
  }

  palco.replaceChildren(barraCampanha(palco, c), area);
  desenhar();
}

// --- Fim de partida e de fase ------------------------------------------------------
function concluirPartida(palco, c, p) {
  const registrar = (disputa) => {
    const adv = p.lados[1].time.id;
    const resultado = resumoPartida(p, disputa);
    registrarConsequencias(c, p);
    // Os outros jogos da fase são simulados agora.
    const outros = simularJogos(c, confrontos(c, c.fase).filter((par) => !par.includes(c.clube)));
    fecharFase(c, c.fase, [resultado, ...outros]);
    const fase = c.fase;
    if (resultado.vencedor !== c.clube) {
      c.status = "eliminado";
      // O torneio segue sem você, para mostrar quem foi campeão.
      for (let f = fase + 1; f < FASES.length; f += 1) fecharFase(c, f, simularJogos(c, confrontos(c, f)));
    } else if (c.fase === FASES.length - 1) {
      c.status = "campeao";
      const titulos = lerPreferencia(CHAVE_TITULOS, {});
      titulos[c.clube] = (titulos[c.clube] || 0) + 1;
      gravarPreferencia(CHAVE_TITULOS, titulos);
    } else c.fase += 1;
    salvar(c);
    telaResultadoFase(palco, c, fase, resultado, adv);
  };
  if (p.lados[0].gols === p.lados[1].gols) telaPenaltis(palco, c, p, registrar);
  else registrar(null);
}

function simularJogos(c, pares) {
  return pares.map(([a, b]) => {
    const sim = simularPartida(configIA(c, a, time(b).forca), configIA(c, b, time(a).forca));
    registrarConsequencias(c, sim.partida);
    return resumoPartida(sim.partida, sim.disputa);
  });
}

// Guarda os resultados na ordem do chaveamento. Suspensão vale só para a fase seguinte, e a
// energia recupera entre as fases.
function fecharFase(c, fase, todos) {
  c.resultados[fase] = confrontos(c, fase).map(([a]) => todos.find((r) => r.a === a || r.b === a));
  c.suspensos = todos.flatMap((r) => r.expulsos);
  for (const id of Object.keys(c.energia)) {
    c.energia[id] = Math.min(100, c.energia[id] + RECUPERACAO);
    if (c.energia[id] >= 100) delete c.energia[id];
  }
}

function resumoPartida(p, disputa) {
  const [A, B] = p.lados;
  const pen = disputa ? golsDisputa(disputa) : [null, null];
  return {
    a: A.time.id, b: B.time.id, ga: A.gols, gb: B.gols, pa: pen[0], pb: pen[1],
    vencedor: p.lados[vencedorDe(p, disputa)].time.id,
    gols: p.lados.flatMap((l) => l.marcadores.map((m) => ({ ...m, clube: l.time.id }))),
    expulsos: p.lados.flatMap((l) => l.expulsos),
  };
}

function registrarConsequencias(c, p) {
  for (const l of p.lados) {
    for (const id of l.jogaram) c.energia[id] = Math.round(l.energia[id]);
    for (const m of l.marcadores) c.artilharia[m.jogador] = (c.artilharia[m.jogador] || 0) + 1;
  }
}

const jogadorPorId = (id) => [...times.values()].map((t) => t.porId.get(id)).find(Boolean);

function placarLinha(r, c) {
  const lado = (id, dir) => h("div", { class: `lado${dir ? " dir" : ""}${r.vencedor === id ? " vencedor" : ""}` },
    dir ? null : escudo(time(id).clube), h("span", {}, time(id).clube.nome), dir ? escudo(time(id).clube) : null);
  const gols = (id, dir) => r.gols.filter((g) => g.clube === id).map((g) =>
    h("div", {}, dir ? `${nomeCurto(jogadorPorId(g.jogador).nome)} ${g.min} ⚽` : `⚽ ${nomeCurto(jogadorPorId(g.jogador).nome)} ${g.min}`));
  return h("div", { class: `cartao partida pr-resultado${r.a === c.clube || r.b === c.clube ? " meu" : ""}` },
    h("div", { class: "placar" }, lado(r.a, false), h("span", { class: "numeros" }, `${r.ga} x ${r.gb}`), lado(r.b, true)),
    r.pa !== null ? h("div", { class: "mudo pequeno pr-centro" }, `Pênaltis: ${r.pa} x ${r.pb}`) : null,
    r.gols.length ? h("div", { class: "gols-partida" }, h("div", {}, gols(r.a, false)), h("div", { class: "dir" }, gols(r.b, true))) : null);
}

function telaResultadoFase(palco, c, fase, resultado, advId) {
  const venceu = resultado.vencedor === c.clube;
  const adv = time(advId);
  const outros = c.resultados[fase].filter((r) => r !== resultado);
  palco.replaceChildren(
    barraCampanha(palco, c),
    h("section", { class: `cartao pr-veredito ${venceu ? "ok" : "fora"}` },
      h("span", { class: "kpi-rotulo" }, FASES[fase]),
      h("p", { class: "pr-grande" }, venceu
        ? (c.status === "campeao" ? "🏆 É campeão!" : `✅ Classificado! Você eliminou o ${adv.clube.nome}.`)
        : `❌ Eliminado pelo ${adv.clube.nome}.`),
      venceu && c.status !== "campeao"
        ? h("p", { class: "mudo pr-sem-margem" }, `Próxima fase: ${FASES[c.fase].toLowerCase()} contra o ${time(adversarioAtual(c)).clube.nome}.`) : null),
    h("div", { class: "grade grade-2" },
      h("section", { class: "cartao" }, h("h2", {}, `Resultados: ${FASES[fase].toLowerCase()}`),
        h("div", { class: "pr-resultados" }, placarLinha(resultado, c), ...outros.map((r) => placarLinha(r, c)))),
      h("section", { class: "cartao" }, h("h2", {}, "Chaveamento"), chaveamento(c))),
    h("div", { class: "pr-centro pr-acoes" },
      h("button", { class: "botao botao-primario pr-botao-grande", type: "button", onclick: () => abrirCampanha(palco, c) },
        c.status === "jogando" ? `Preparar a ${FASES[c.fase].toLowerCase()} ▶` : "Ver o resumo da campanha ▶")));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function chaveamento(c) {
  return h("div", { class: "pr-chave" }, FASES.map((nome, fase) => {
    const pares = fase === 0 || c.resultados[fase - 1].length ? confrontos(c, fase) : [];
    const caixas = Array.from({ length: [4, 2, 1][fase] }, (_, k) => {
      const par = pares[k] || [];
      const r = c.resultados[fase][k];
      const linhaTime = (id) => {
        if (!id) return h("div", { class: "pr-chave-time vazio" }, h("span", {}, "A definir"));
        const placar = r ? (r.a === id ? [r.ga, r.pa] : [r.gb, r.pb]) : null;
        const classes = ["pr-chave-time", r?.vencedor === id && "vencedor", r && r.vencedor !== id && "perdedor", id === c.clube && "meu"];
        return h("div", { class: classes.filter(Boolean).join(" ") },
          escudo(time(id).clube), h("span", {}, time(id).clube.nome),
          h("strong", {}, placar ? `${placar[0]}${placar[1] !== null ? ` (${placar[1]})` : ""}` : ""));
      };
      return h("div", { class: "pr-chave-jogo" }, linhaTime(par[0]), linhaTime(par[1]));
    });
    return h("div", { class: "pr-chave-coluna" }, h("span", { class: "kpi-rotulo" }, nome), ...caixas);
  }));
}

// --- Fim da campanha -----------------------------------------------------------------
function telaFim(palco, c) {
  const t = time(c.clube);
  const campeao = c.status === "campeao";
  const titulos = lerPreferencia(CHAVE_TITULOS, {})[c.clube] || 0;
  const meus = c.resultados.flat().filter((r) => r.a === c.clube || r.b === c.clube);
  const ultimo = meus.at(-1);
  const faseFinal = c.resultados.findIndex((f) => f.includes(ultimo));
  const artilharia = Object.entries(c.artilharia).sort((a, b) => b[1] - a[1]).slice(0, 5);
  const novaCampanha = (mesmoClube) => {
    descartar();
    if (mesmoClube) iniciarCampanha(palco, c.clube, c.modo);
    else telaInicio(palco);
  };
  palco.replaceChildren(
    barraCampanha(palco, c),
    h("section", { class: `cartao pr-final${campeao ? " campeao" : ""}` },
      campeao ? h("div", { class: "pr-final-icone", "aria-hidden": "true" }, "🏆") : null,
      escudo(t.clube, "escudo-lg"),
      h("h2", {}, campeao ? `${t.clube.nome}, campeão da Prancheta 2024!` : `Fim da campanha do ${t.clube.nome}`),
      h("p", { class: "mudo" }, campeao
        ? `${titulos === 1 ? "Primeiro título" : `Título número ${titulos}`} com este clube neste navegador.${nEstrelas(t.forca) <= 2 ? " Com esse elenco, foi uma façanha!" : ""}`
        : `Eliminado ${NA_FASE[faseFinal]} pelo ${time(ultimo.vencedor).clube.nome}. O campeão foi o ${time(c.resultados[2][0].vencedor).clube.nome}.`),
      h("div", { class: "pr-final-botoes" },
        h("button", { class: "botao botao-primario", type: "button", onclick: () => novaCampanha(true) }, `Jogar de novo com o ${t.clube.nome}`),
        h("button", { class: "botao", type: "button", onclick: () => novaCampanha(false) }, "Escolher outro clube"))),
    h("div", { class: "grade grade-2" },
      h("section", { class: "cartao" }, h("h2", {}, "Sua campanha"),
        h("div", { class: "pr-resultados" }, meus.map((r) => placarLinha(r, c)))),
      h("section", { class: "cartao" }, h("h2", {}, "Artilharia do torneio"),
        artilharia.length ? h("ol", { class: "lista-rank" }, artilharia.map(([id, n], i) => {
          const j = jogadorPorId(id);
          return h("li", {}, h("span", { class: "mudo" }, `${i + 1}º`), botao(coresDoTime(time(j.clube).clube), j.nota),
            h("span", { class: "nome" }, j.nome, h("div", { class: "mudo pequeno" }, time(j.clube).clube.nome)), h("span", { class: "valor" }, n));
        })) : h("p", { class: "mudo" }, "Nenhum gol marcado."))),
    h("section", { class: "cartao pr-acoes" }, h("h2", {}, "Chaveamento"), chaveamento(c)));
}
