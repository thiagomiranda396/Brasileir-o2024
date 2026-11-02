import { h, cabecalho, cartao, faixaKpis, secao, rota, filtros } from "../ui.js";
import { escudo, foto } from "../imagens.js";
import { colunas } from "../graficos.js";
import { num, pct, contar, resumoCampeonato } from "../dados.js";

const PERIODOS = {
  todo: { nome: "Campeonato inteiro", rodadas: [1, 38] },
  turno1: { nome: "1º turno (rodadas 1 a 19)", rodadas: [1, 19] },
  turno2: { nome: "2º turno (rodadas 20 a 38)", rodadas: [20, 38] },
};

export function render(main, d) {
  let periodo = "todo";
  const conteudo = h("div", { class: "pilha-pagina" });
  main.append(cabecalho("Brasileirão Série A 2024", "20 clubes, 38 rodadas e 380 partidas, de abril a dezembro."), conteudo);
  filtros(["Período", h("select", { onchange: (ev) => { periodo = ev.target.value; desenhar(); } },
    Object.entries(PERIODOS).map(([k, p]) => h("option", { value: k }, p.nome)))]);
  const desenhar = () => { conteudo.replaceChildren(); painel(conteudo, d, periodo); };
  desenhar();
}

// Classificação de um trecho do campeonato, pelos critérios da CBF (sem confronto direto).
function tabelaDoPeriodo(d, [ini, fim]) {
  if (ini === 1) return d.classificacao[fim - 1];
  const linhas = [...d.participacoesPorClube].map(([clube, lista]) => {
    const l = { clube, pts: 0, v: 0, gp: 0, gc: 0 };
    for (const x of lista) if (x.rodada >= ini && x.rodada <= fim) {
      l.pts += x.pontos; l.gp += x.gp; l.gc += x.gc; if (x.resultado === "V") l.v += 1;
    }
    l.sg = l.gp - l.gc;
    return l;
  });
  return linhas.sort((a, b) => b.pts - a.pts || b.v - a.v || b.sg - a.sg || b.gp - a.gp);
}

function painel(main, d, periodo) {
  const { rodadas } = PERIODOS[periodo];
  const [ini, fim] = rodadas;
  const naFaixa = (r) => r >= ini && r <= fim;
  const partidas = d.partidas.filter((p) => naFaixa(p.r));
  const ids = new Set(partidas.map((p) => p.id));
  const gols = d.gols.filter((g) => ids.has(g.partida));
  const c = resumoCampeonato(partidas, gols, d.cartoes.filter((k) => ids.has(k.partida)));
  const tabela = tabelaDoPeriodo(d, rodadas);
  const [lider, vice] = tabela;
  const campeao = d.clubes.get(lider.clube);
  const rotuloLider = { todo: "Campeão", turno1: "Campeão do 1º turno", turno2: "Melhor campanha do 2º turno" }[periodo];

  // 1. O resultado do período e os quatro números que o resumem.
  main.append(h("div", { class: "heroi" },
    h("a", { class: "cartao campeao", href: rota("clubes", campeao.id),
      style: { "--cor-clube": campeao.cor1 } },
      escudo(campeao, "escudo-lg"),
      h("div", {},
        h("div", { class: "rotulo-secao" }, rotuloLider),
        h("div", { class: "campeao-nome" }, campeao.nome),
        h("div", { class: "mudo" }, `${lider.pts} pontos, ${lider.pts - vice.pts} à frente do ${d.clubes.get(vice.clube).nome}`))),
    faixaKpis([
      ["Gols", num(c.gols), `${num(c.media, 2)} por jogo`],
      ["Vitórias do mandante", pct((100 * c.mandante) / c.partidas, 0), `${pct((100 * c.visitante) / c.partidas, 0)} do visitante`],
      ["Empates", pct((100 * c.empates) / c.partidas, 0), `${c.zeroAZero} terminaram 0 a 0`],
      ["Cartões", num(c.amarelos + c.vermelhos), `${c.vermelhos} vermelhos`],
    ], { colunas: 2 })));

  // 2. Os gols no tempo: ao longo do período e ao longo do jogo.
  const golsRodada = h("div");
  const golsFaixa = h("div");
  const nRodadas = fim - ini + 1;
  main.append(secao("Quando saíram os gols", null, h("div", { class: "grade grade-2" },
    cartao("Por rodada", `Média de ${num(c.gols / nRodadas, 1)} gols por rodada`, golsRodada),
    cartao("Por minuto de jogo", "Faixas de 15 minutos; acréscimos contam no fim de cada tempo", golsFaixa))));
  colunas(golsRodada, c.golsPorRodada.slice(ini - 1, fim).map((v, i) => ({ rotulo: String(ini + i), valor: v, titulo: `Rodada ${ini + i}`, legenda: "gols" })),
    { rotuloEixo: (dd, i) => ((ini + i) % 5 === 0 || i === 0 ? dd.rotulo : ""), a11y: "Gols por rodada" });
  colunas(golsFaixa, c.golsPorFaixa.map((f) => ({ rotulo: `${f.faixa}'`, valor: f.gols, titulo: `Minutos ${f.faixa}`, legenda: "gols" })),
    { a11y: "Gols por faixa de minutos" });

  // 3. Destaques: seis cartões com a mesma estrutura (rótulo, número, quem).
  const est = [...d.participacoesPorClube].map(([id, lista]) => {
    const parte = (mando) => {
      const l = lista.filter((x) => naFaixa(x.rodada) && (!mando || x.mando === mando));
      const pts = l.reduce((s, x) => s + x.pontos, 0);
      return { gp: l.reduce((s, x) => s + x.gp, 0), gc: l.reduce((s, x) => s + x.gc, 0), aprov: l.length ? (100 * pts) / (3 * l.length) : 0 };
    };
    return { id, total: parte(), casa: parte("Casa"), fora: parte("Fora") };
  });
  const melhor = (f) => [...est].sort((a, b) => f(b) - f(a))[0];
  const ataque = melhor((e) => e.total.gp);
  const defesa = melhor((e) => -e.total.gc);
  const casa = melhor((e) => e.casa.aprov);
  const fora = melhor((e) => e.fora.aprov);
  const golsJogador = contar(gols.filter((g) => g.tipo !== "Contra"), (g) => g.jogador);
  const topGols = Math.max(...golsJogador.values());
  const artilheiros = [...golsJogador].filter(([, n]) => n === topGols).map(([id]) => d.jogadores.get(id));
  const garcom = [...d.jogadores.values()].filter((j) => j.ast !== null).sort((a, b) => b.ast - a.ast)[0];

  const destaque = (rotulo, valor, unidade, quem, link) => h("a", { class: "cartao destaque", href: link },
    h("div", { class: "kpi-rotulo" }, rotulo),
    h("div", { class: "destaque-numero" }, h("strong", {}, valor), h("span", {}, unidade)),
    h("div", { class: "destaque-quem" }, quem));
  const doClube = (e) => [escudo(d.clubes.get(e.id)), h("span", {}, d.clubes.get(e.id).nome)];
  const doJogador = (j) => [foto(j, d.clubes.get(j.clube), "foto-sm"), h("span", {}, j.nome)];

  main.append(secao("Destaques", periodo === "todo" ? null : "Assistências: só há o ranking do campeonato inteiro.", h("div", { class: "grade grade-destaques" },
    destaque("Artilharia", topGols, "gols", artilheiros.slice(0, 3).flatMap((j, i) => [i ? h("span", { class: "mudo" }, "e") : null, ...doJogador(j)]), rota("jogadores", "gols")),
    destaque(periodo === "todo" ? "Assistências" : "Assistências (campeonato)", garcom.ast, "passes para gol", doJogador(garcom), rota("jogadores", "assistencias")),
    destaque("Melhor ataque", ataque.total.gp, "gols marcados", doClube(ataque), rota("clubes", ataque.id)),
    destaque("Melhor defesa", defesa.total.gc, "gols sofridos", doClube(defesa), rota("clubes", defesa.id)),
    destaque("Melhor mandante", pct(casa.casa.aprov, 0), "dos pontos em casa", doClube(casa), rota("clubes", casa.id)),
    destaque("Melhor visitante", pct(fora.fora.aprov, 0), "dos pontos fora", doClube(fora), rota("clubes", fora.id)))));

  main.append(h("p", { class: "proximo" }, h("a", { href: rota("classificacao") }, "Ver a classificação rodada a rodada →")));
}
