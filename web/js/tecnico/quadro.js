// Prancheta 2024: componentes visuais do jogo de técnico.
//
// - botao(): o jogador como um botão de futebol de mesa, nas cores do clube, com a nota no disco.
// - quadroTatico(): campo + banco para escalar e substituir (tocar em dois jogadores ou arrastar).
// - campoDeJogo(): o campo visto de cima durante a partida, com os 22 botões e a bola se mexendo.

import { h } from "../ui.js";
import { vagasDaFormacao, SETORES } from "./elenco.js";
import { nomeCurto } from "./motor.js";

// --- Cores ----------------------------------------------------------------------
function rgb(hex) {
  const v = parseInt(hex.replace("#", ""), 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
}
function luminancia(hex) {
  const [r, g, b] = rgb(hex).map((c) => {
    const x = c / 255;
    return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
const distancia = (a, b) => Math.hypot(...rgb(a).map((c, i) => c - rgb(b)[i]));

// Uniforme do time; com rival de cor parecida, o time usa a cor secundária (ou branco).
export function coresDoTime(clube, rival = null) {
  let fundo = clube.cor1, borda = clube.cor2;
  if (rival && distancia(fundo, rival.cor1) < 90) {
    fundo = distancia(clube.cor2, rival.cor1) >= 90 ? clube.cor2 : "#f4f4f2";
    borda = clube.cor1;
  }
  if (distancia(fundo, borda) < 60) borda = luminancia(fundo) > 0.4 ? "#111111" : "#f4f4f2";
  return { fundo, borda, texto: luminancia(fundo) > 0.36 ? "#111111" : "#ffffff" };
}

// Variáveis CSS (--x) precisam de setProperty; o h() só copia propriedades comuns.
export function comVariaveis(el, vars) {
  for (const [k, v] of Object.entries(vars)) el.style.setProperty(k, v);
  return el;
}

// --- Botão ------------------------------------------------------------------------
export function botao(cores, conteudo, { classe = "", titulo = null } = {}) {
  return comVariaveis(h("span", { class: `pr-botao ${classe}`.trim(), title: titulo },
    h("span", { class: "pr-botao-disco" }, conteudo)),
  { "--b-fundo": cores.fundo, "--b-borda": cores.borda, "--b-texto": cores.texto });
}

export function barraEnergia(energia) {
  const cor = energia >= 75 ? "var(--bom)" : energia >= 55 ? "var(--aviso)" : "var(--ruim)";
  return h("span", { class: "pr-energia", title: `Energia ${Math.round(energia)}%`, "aria-label": `Energia ${Math.round(energia)}%` },
    h("i", { style: { width: `${energia}%`, background: cor } }));
}

// --- Quadro tático ------------------------------------------------------------------
// cfg: {
//   cores, formacao(), vagas(): [{ jogador|null, setor, marca? }], banco(): [{ jogador, bloqueado?, motivo? }],
//   nota(j, setor), energia(id),
//   aoTrocar(origem, destino) com origem/destino = { vaga: i } ou { banco: id }; devolve texto de aviso ou nada,
//   rodape?(): elemento extra abaixo do detalhe (ex.: confirmação de substituição)
// }
// Nome completo no computador; no celular, o campo mostra só o último nome (ver CSS).
function apelido(j) {
  const nome = nomeCurto(j.nome);
  const ultimo = nome.split(" ").slice(-1)[0];
  return ultimo === nome ? nome : [h("span", { class: "longo" }, nome), h("span", { class: "curto" }, ultimo)];
}

export function quadroTatico(cfg) {
  let selecionado = null;
  const campo = h("div", { class: "pr-quadro-campo" });
  const banco = h("div", { class: "pr-banco" });
  const detalhe = h("div", { class: "pr-detalhe", role: "status" });
  const el = h("div", { class: "pr-quadro" }, campo, h("div", { class: "pr-quadro-lado" }, detalhe, banco));
  let aviso = "";

  const igual = (a, b) => a && b && a.vaga === b.vaga && a.banco === b.banco;
  const jogadorDe = (alvo) => (alvo.vaga !== undefined ? cfg.vagas()[alvo.vaga]?.jogador : cfg.banco().find((b) => b.jogador.id === alvo.banco)?.jogador);

  function escolher(alvo) {
    const item = alvo.banco !== undefined ? cfg.banco().find((b) => b.jogador.id === alvo.banco) : null;
    if (item?.bloqueado) {
      aviso = `${item.jogador.nome}: ${item.motivo}.`;
      selecionado = null;
    } else if (!selecionado) {
      selecionado = alvo;
      aviso = "";
    } else if (igual(selecionado, alvo)) {
      selecionado = null;
    } else {
      const origem = selecionado;
      selecionado = null;
      aviso = cfg.aoTrocar(origem, alvo) || "";
    }
    desenhar();
  }

  // Arrastar com o dedo ou o mouse; um toque sem arrastar vale como clique.
  function arrastavel(elemento, alvo) {
    elemento.dataset.alvo = JSON.stringify(alvo);
    elemento.addEventListener("pointerdown", (e) => {
      if (e.button !== 0) return;
      const x0 = e.clientX, y0 = e.clientY;
      let fantasma = null;
      const mover = (m) => {
        if (!fantasma && Math.hypot(m.clientX - x0, m.clientY - y0) > 8) {
          fantasma = elemento.cloneNode(true);
          fantasma.classList.add("pr-fantasma");
          (el.closest("dialog") || document.body).append(fantasma);
          elemento.classList.add("arrastando");
        }
        if (fantasma) {
          m.preventDefault();
          fantasma.style.left = `${m.clientX}px`;
          fantasma.style.top = `${m.clientY}px`;
        }
      };
      const soltar = (u) => {
        window.removeEventListener("pointermove", mover);
        window.removeEventListener("pointerup", soltar);
        window.removeEventListener("pointercancel", soltar);
        if (!fantasma) { if (u.type === "pointerup") escolher(alvo); return; }
        fantasma.remove();
        elemento.classList.remove("arrastando");
        if (u.type !== "pointerup") return;
        const sob = document.elementFromPoint(u.clientX, u.clientY)?.closest("[data-alvo]");
        if (sob && sob !== elemento && el.contains(sob)) {
          selecionado = alvo;
          escolher(JSON.parse(sob.dataset.alvo));
        }
      };
      window.addEventListener("pointermove", mover, { passive: false });
      window.addEventListener("pointerup", soltar);
      window.addEventListener("pointercancel", soltar);
    });
    elemento.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); escolher(alvo); }
    });
  }

  function peca(j, setorVaga, alvo, extra = {}) {
    const fora = j && setorVaga && j.setor !== setorVaga;
    const nota = j ? Math.round(cfg.nota(j, setorVaga || j.setor)) : "+";
    const el2 = h("div", {
      class: `pr-peca${igual(selecionado, alvo) ? " selecionada" : ""}${fora ? " fora-posicao" : ""}${extra.bloqueado ? " bloqueada" : ""}`,
      tabindex: "0", role: "button", style: extra.style,
      "aria-label": j ? `${j.nome}, ${SETORES[j.setor]}${fora ? `, improvisado como ${SETORES[setorVaga]}` : ""}, nota ${nota}${extra.motivo ? `, ${extra.motivo}` : ""}` : "Vaga livre",
    },
    botao(j ? cfg.cores : { fundo: "transparent", borda: "rgba(255,255,255,.7)", texto: "#fff" }, nota),
    h("span", { class: "pr-peca-nome" }, j ? apelido(j) : "Vaga", extra.marca || ""),
    h("span", { class: "pr-peca-setor" }, setorVaga || j?.setor || ""),
    j ? barraEnergia(cfg.energia(j.id)) : null);
    arrastavel(el2, alvo);
    return el2;
  }

  function desenhar() {
    const vagas = vagasDaFormacao(cfg.formacao());
    const ocupadas = cfg.vagas();
    campo.replaceChildren(
      h("div", { class: "pr-marcas" }, h("i", { class: "area cima" }), h("i", { class: "area baixo" }), h("i", { class: "circulo" }), h("i", { class: "meio" })),
      ...vagas.map((v, i) => (ocupadas[i]?.ausente ? null : peca(ocupadas[i]?.jogador, v.setor, { vaga: i }, {
        style: { left: `${v.x}%`, top: `${v.y}%` }, marca: ocupadas[i]?.marca,
      }))).filter(Boolean));

    const itens = cfg.banco();
    banco.replaceChildren(h("h3", {}, `Banco (${itens.length})`),
      ...["GOL", "DEF", "MEI", "ATA"].map((setor) => {
        const doSetor = itens.filter((b) => b.jogador.setor === setor);
        return doSetor.length ? h("div", { class: "pr-banco-grupo" },
          h("span", { class: "pr-banco-rotulo" }, SETORES[setor]),
          h("div", { class: "pr-banco-pecas" }, doSetor.map((b) => peca(b.jogador, null, { banco: b.jogador.id }, { bloqueado: b.bloqueado, motivo: b.motivo })))) : null;
      }).filter(Boolean));

    const j = selecionado ? jogadorDe(selecionado) : null;
    const setorVaga = selecionado?.vaga !== undefined ? vagas[selecionado.vaga].setor : null;
    detalhe.replaceChildren(...[
      j ? h("div", { class: "pr-detalhe-jogador" },
        botao(cfg.cores, Math.round(cfg.nota(j, setorVaga || j.setor)), { classe: "grande" }),
        h("div", {},
          h("strong", {}, j.nome),
          h("div", { class: "mudo pequeno" }, `${SETORES[j.setor]}${setorVaga && setorVaga !== j.setor ? ` · improvisado como ${SETORES[setorVaga].toLowerCase()}` : ""}`),
          h("div", { class: "mudo pequeno" }, [j.gols ? `${j.gols} gol${j.gols > 1 ? "s" : ""} em 2024` : null, j.ast ? `${j.ast} assistências` : null, j.selecao ? "seleção do campeonato" : null].filter(Boolean).join(" · ") || "Elenco 2024"),
          h("div", { class: "pr-detalhe-energia" }, h("span", { class: "mudo pequeno" }, "Energia"), barraEnergia(cfg.energia(j.id))),
          h("p", { class: "pequeno pr-dica" }, selecionado.vaga !== undefined ? "Agora toque em quem vai entrar no lugar dele (no banco) ou em outro titular para trocar de posição." : "Agora toque no titular que vai sair."))) :
        h("p", { class: "pequeno pr-dica" }, aviso || "Toque num jogador e depois em outro para trocar os dois. Também dá para arrastar um botão até o outro."),
      cfg.rodape ? cfg.rodape() : null].filter(Boolean));
  }

  desenhar();
  return { el, desenhar, limpar: () => { selecionado = null; aviso = ""; desenhar(); } };
}

// --- Campo de jogo (visto de cima) ----------------------------------------------------
const limitar = (v, a, b) => Math.max(a, Math.min(b, v));

export function campoDeJogo(p, coresLados) {
  const pecas = new Map();   // id do jogador -> elemento
  const bola = h("span", { class: "pr-bola", "aria-hidden": "true" });
  const faixaGol = h("div", { class: "pr-gol-faixa", "aria-hidden": "true" });
  const camada = h("div", { class: "pr-jogadores" });
  const el = h("div", { class: "pr-gramado", role: "img", "aria-label": "Campo visto de cima com os dois times" },
    h("div", { class: "pr-gramado-linhas" },
      h("i", { class: "meio" }), h("i", { class: "circulo" }), h("i", { class: "ponto" }),
      h("i", { class: "area esq" }), h("i", { class: "area dir" }), h("i", { class: "pequena esq" }), h("i", { class: "pequena dir" }),
      h("i", { class: "gol esq" }), h("i", { class: "gol dir" })),
    camada, bola, faixaGol);
  let estadoBola = { x: 50, y: 50 };

  // Posição base: o seu time ataca para a direita; o rival, para a esquerda.
  function base(lado, x) {
    const v = vagasDaFormacao(p.lados[lado].formacao)[x.vaga];
    const X = 5 + (90 - v.y) * 0.52;
    return lado === 0 ? { x: X, y: v.x } : { x: 100 - X, y: 100 - v.x };
  }

  function sincronizarPecas() {
    const vivos = new Set();
    p.lados.forEach((l, lado) => {
      for (const x of l.emCampo) {
        const id = x.jogador.id;
        vivos.add(id);
        let e = pecas.get(id);
        if (!e) {
          e = h("span", { class: `pr-jogador lado-${lado}` },
            botao(coresLados[lado], x.jogador.nota),
            h("span", { class: "pr-jogador-nome" }, nomeCurto(x.jogador.nome).split(" ").slice(-1)[0]));
          const pos = base(lado, x);
          e.style.left = `${pos.x}%`;
          e.style.top = `${pos.y}%`;
          camada.append(e);
          pecas.set(id, e);
        }
        e.classList.toggle("goleiro", x.setor === "GOL");
      }
    });
    for (const [id, e] of pecas) {
      if (!vivos.has(id)) { e.remove(); pecas.delete(id); }
    }
  }

  function posicionar(alvoBola, duracao, agito = 1.5) {
    const desloc = (alvoBola.x - 50) * 0.42;
    const posicoes = new Map();
    p.lados.forEach((l, lado) => {
      for (const x of l.emCampo) {
        const b = base(lado, x);
        const goleiro = x.setor === "GOL";
        // Ninguém da linha recua para dentro da pequena área do próprio goleiro.
        const [min, max] = goleiro ? [2.5, 97.5] : lado === 0 ? [10, 97.5] : [2.5, 90];
        const px = limitar(b.x + desloc * (goleiro ? 0.08 : 1) + (Math.random() - 0.5) * 2 * agito, min, max);
        const py = limitar(b.y + (alvoBola.y - b.y) * (goleiro ? 0.1 : 0.16) + (Math.random() - 0.5) * 2 * agito, 5, 95);
        posicoes.set(x.jogador.id, { x: px, y: py, lado });
      }
    });
    for (const [id, pos] of posicoes) {
      const e = pecas.get(id);
      e.style.transitionDuration = `${duracao}ms`;
      e.style.left = `${pos.x}%`;
      e.style.top = `${pos.y}%`;
    }
    return posicoes;
  }

  function moverBola(x, y, duracao) {
    estadoBola = { x, y };
    bola.style.transitionDuration = `${duracao}ms`;
    bola.style.left = `${x}%`;
    bola.style.top = `${y}%`;
  }

  // Quem está mais perto do ponto (do lado indicado) conduz a bola.
  function maisPerto(posicoes, lado, alvo, excluirGoleiro = true) {
    let melhor = null, menor = Infinity;
    for (const [id, pos] of posicoes) {
      if (pos.lado !== lado) continue;
      if (excluirGoleiro && pecas.get(id)?.classList.contains("goleiro")) continue;
      const d = Math.hypot(pos.x - alvo.x, pos.y - alvo.y);
      if (d < menor) { menor = d; melhor = { id, ...pos }; }
    }
    return melhor;
  }

  function destacar(id, classe, ms) {
    const e = pecas.get(id);
    if (!e) return;
    e.classList.add(classe);
    setTimeout(() => e.classList.remove(classe), ms);
  }

  function mostrarGol(lado) {
    const l = p.lados[lado];
    faixaGol.textContent = "GOL!";
    faixaGol.style.setProperty("--g-fundo", coresLados[lado].fundo);
    faixaGol.style.setProperty("--g-texto", coresLados[lado].texto);
    faixaGol.classList.remove("ativa");
    void faixaGol.offsetWidth;
    faixaGol.classList.add("ativa");
    faixaGol.title = l.time.clube.nome;
  }

  // Anima um minuto. posseEu: fração da posse do seu time neste minuto.
  function animar(novos, posseEu, intervalo) {
    sincronizarPecas();
    const dur = Math.max(120, Math.min(650, intervalo * 0.9));
    if (p.estado === "intervalo" || p.estado === "fim") {
      posicionar({ x: 50, y: 50 }, dur, 0);
      moverBola(50, 50, dur);
      return;
    }
    const lance = novos.find((e) => e.tipo === "gol") || novos.find((e) => e.tipo === "defesa" || e.tipo === "chance");
    const dono = lance ? lance.lado : Math.random() < posseEu ? 0 : 1;
    const sentido = dono === 0 ? 1 : -1;
    const alvo = lance
      ? { x: 50 + sentido * (30 + Math.random() * 8), y: 32 + Math.random() * 36 }
      : { x: 50 + sentido * (Math.random() * 40 - 12), y: 12 + Math.random() * 76 };
    const posicoes = posicionar(alvo, dur);
    const autor = lance?.jogador && posicoes.has(lance.jogador) ? { id: lance.jogador, ...posicoes.get(lance.jogador) } : maisPerto(posicoes, dono, alvo);
    if (autor) moverBola(autor.x + sentido * 1.6, autor.y + 1.5, dur);
    for (const e of novos) {
      if ((e.tipo === "amarelo" || e.tipo === "vermelho") && e.jogador) destacar(e.jogador, e.tipo === "amarelo" ? "cartao-amarelo" : "cartao-vermelho", 1800);
    }
    if (!lance) return;
    // Segundo tempo do lance: a finalização.
    setTimeout(() => {
      if (!el.isConnected) return;
      const golX = dono === 0 ? 99 : 1;
      if (lance.tipo === "gol") {
        moverBola(golX, 46 + Math.random() * 8, dur * 0.6);
        mostrarGol(dono);
      } else if (lance.tipo === "defesa") {
        const goleiro = [...posicoes].find(([id, pos]) => pos.lado !== dono && pecas.get(id)?.classList.contains("goleiro"));
        if (goleiro) { moverBola(goleiro[1].x - sentido * 1.2, goleiro[1].y, dur * 0.6); destacar(goleiro[0], "defendeu", 900); }
      } else {
        moverBola(dono === 0 ? 101 : -1, Math.random() < 0.5 ? 34 : 66, dur * 0.6);
      }
    }, dur * 0.55);
  }

  sincronizarPecas();
  posicionar({ x: 50, y: 50 }, 0, 0);
  moverBola(50, 50, 0);
  return { el, animar, sincronizar: () => { sincronizarPecas(); posicionar(estadoBola, 300, 0); } };
}
