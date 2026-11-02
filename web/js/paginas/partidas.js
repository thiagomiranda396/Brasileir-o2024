import { h, cabecalho, filtros } from "../ui.js";
import { escudo } from "../imagens.js";
import { dataCurta, minutoTexto } from "../dados.js";

export function render(main, d, [rodadaParam]) {
  let rodada = Number(rodadaParam) >= 1 && Number(rodadaParam) <= 38 ? Number(rodadaParam) : 38;
  let clubeFiltro = "";

  main.append(cabecalho("Partidas", "Todos os 380 jogos, com gols minuto a minuto e expulsões. Escolha a rodada ou o clube na barra lateral."));
  const selRodada = h("select", { "aria-label": "Rodada", onchange: (ev) => { rodada = Number(ev.target.value); history.replaceState(null, "", `#/partidas/${rodada || ""}`); desenhar(); } },
    h("option", { value: "0" }, "Todas as rodadas"),
    Array.from({ length: 38 }, (_, i) => h("option", { value: String(i + 1), selected: i + 1 === rodada }, `Rodada ${i + 1}`)));
  const selClube = h("select", { "aria-label": "Clube", onchange: (ev) => { clubeFiltro = ev.target.value; desenhar(); } },
    h("option", { value: "" }, "Todos os clubes"),
    [...d.clubes.values()].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR")).map((c) => h("option", { value: c.id }, c.nome)));
  const anterior = h("button", { class: "botao", type: "button", "aria-label": "Rodada anterior", onclick: () => mover(-1) }, "◀");
  const proxima = h("button", { class: "botao", type: "button", "aria-label": "Próxima rodada", onclick: () => mover(1) }, "▶");
  const resumo = h("p", { class: "mudo" });
  const lista = h("div", { class: "lista-partidas" });
  filtros(["Rodada", h("div", { class: "linha-filtro" }, anterior, selRodada, proxima)], ["Clube", selClube]);
  main.append(resumo, lista);

  function mover(delta) {
    rodada = Math.min(38, Math.max(1, (rodada || 1) + delta));
    selRodada.value = String(rodada);
    history.replaceState(null, "", `#/partidas/${rodada}`);
    desenhar();
  }

  function desenhar() {
    const jogos = d.partidas.filter((p) => (!rodada || p.r === rodada) && (!clubeFiltro || p.m === clubeFiltro || p.v === clubeFiltro))
      .sort((a, b) => a.data.localeCompare(b.data) || (a.hora || "").localeCompare(b.hora || "") || a.id - b.id);
    const gols = jogos.reduce((s, p) => s + p.total, 0);
    resumo.textContent = `${jogos.length} jogos · ${gols} gols · média ${(gols / Math.max(1, jogos.length)).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} por jogo`;
    lista.replaceChildren(...jogos.map((p) => cartaoPartida(d, p)));
  }
  desenhar();
}

function cartaoPartida(d, p) {
  const m = d.clubes.get(p.m), v = d.clubes.get(p.v);
  const gols = d.golsPorPartida.get(p.id) || [];
  const vermelhos = d.cartoes.filter((k) => k.partida === p.id && k.tipo === "V");
  const linhaGol = (g) => {
    const j = d.jogadores.get(g.jogador);
    const sufixo = g.tipo === "Pênalti" ? " (pên.)" : g.tipo === "Contra" ? " (contra)" : "";
    return h("a", { href: `#/jogadores/jogador/${j.id}` }, `⚽ ${j.nome} ${minutoTexto(g)}${sufixo}`);
  };
  const lado = (clubeId) => [
    ...gols.filter((g) => g.beneficiado === clubeId).map(linhaGol),
    ...vermelhos.filter((k) => k.clube === clubeId).map((k) => h("span", {}, `🟥 ${d.jogadores.get(k.jogador).nome} ${minutoTexto(k)}`)),
  ];
  const resultado = p.gm > p.gv ? "m" : p.gm < p.gv ? "v" : "e";
  return h("article", { class: "cartao partida" },
    h("div", { class: "partida-topo" },
      h("span", {}, `R${p.r} · ${dataCurta(p.data)}${p.hora ? ` · ${p.hora}` : ""}`),
      h("span", { style: { overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, p.estadio)),
    h("div", { class: "placar" },
      h("a", { class: "lado", href: `#/clubes/${m.id}`, style: { color: "inherit", textDecoration: "none", fontWeight: resultado === "m" ? 800 : 600 } }, escudo(m), h("span", {}, m.nome)),
      h("span", { class: "numeros", "aria-label": `${p.gm} a ${p.gv}` }, `${p.gm} – ${p.gv}`),
      h("a", { class: "lado dir", href: `#/clubes/${v.id}`, style: { color: "inherit", textDecoration: "none" } }, h("span", {}, v.nome), escudo(v))),
    p.gm1 !== null ? h("div", { class: "mudo pequeno", style: { textAlign: "center" } }, `Intervalo: ${p.gm1} – ${p.gv1}`) : null,
    gols.length || vermelhos.length
      ? h("div", { class: "gols-partida" }, h("div", {}, lado(m.id).map((x) => h("div", {}, x))), h("div", { class: "dir" }, lado(v.id).map((x) => h("div", {}, x))))
      : null);
}
