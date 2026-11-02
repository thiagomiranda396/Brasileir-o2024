// Testes do jogo de técnico (web/js/tecnico), rodados em Node por test_jogo_tecnico.py.
// Usa sorteio com semente para que os resultados sejam reprodutíveis.
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

const WEB = new URL("../web/", import.meta.url);
const { montar } = await import(new URL("js/dados.js", WEB));
const E = await import(new URL("js/tecnico/elenco.js", WEB));
const M = await import(new URL("js/tecnico/motor.js", WEB));

const d = montar(JSON.parse(readFileSync(new URL("data/brasileirao2024.json", WEB), "utf8")));
const times = E.prepararElencos(d);

function semente(s) {
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const cfg = (id, extra = {}) => {
  const t = times.get(id);
  return { time: t, formacao: t.formacao, titulares: E.escalarAutomatico(t, t.formacao), postura: "equilibrada", ...extra };
};
const testes = [];
const teste = (nome, fn) => testes.push([nome, fn]);

teste("escalação automática válida para os 20 clubes e todas as formações", () => {
  assert.equal(times.size, 20);
  for (const t of times.values()) {
    for (const f of Object.keys(E.FORMACOES)) {
      const ids = E.escalarAutomatico(t, f);
      assert.equal(ids.length, 11, t.id);
      assert.equal(new Set(ids).size, 11, `${t.id} ${f}: repetido`);
      assert.ok(ids.every((id) => t.porId.has(id)), `${t.id}: jogador de outro clube`);
      assert.equal(t.porId.get(ids[0]).setor, "GOL", `${t.id}: sem goleiro`);
    }
  }
});

teste("força acompanha a classificação real de 2024", () => {
  const lista = [...times.values()].sort((a, b) => a.posicao - b.posicao);
  assert.equal(lista[0].id, "BOT");
  assert.equal(Math.max(...lista.map((t) => t.forca)), times.get("BOT").forca);
  const fracos = [...lista].sort((a, b) => a.forca - b.forca).slice(0, 3).map((t) => t.id);
  assert.ok(fracos.includes("CUI") && fracos.includes("ATG"), fracos.join());
  // Correlação de Spearman entre posição e força (com sinal trocado).
  const n = lista.length;
  const rank = [...lista].sort((a, b) => b.forca - a.forca).map((t) => t.id);
  const d2 = lista.reduce((s, t, i) => s + (i - rank.indexOf(t.id)) ** 2, 0);
  assert.ok(1 - (6 * d2) / (n * (n * n - 1)) > 0.85);
});

teste("Botafogo é favorito contra o lanterna, mas zebra é possível", () => {
  const r = semente(42);
  let vitorias = 0, derrotas = 0, gols = 0;
  for (let k = 0; k < 600; k += 1) {
    const { partida } = M.simularPartida(cfg("BOT"), cfg("CUI"), r);
    const [a, b] = partida.lados.map((l) => l.gols);
    gols += a + b;
    if (a > b) vitorias += 1;
    if (a < b) derrotas += 1;
  }
  assert.ok(vitorias / 600 > 0.7, `vitórias ${vitorias}`);
  assert.ok(derrotas > 0, "sem nenhuma zebra");
  assert.ok(gols / 600 > 2 && gols / 600 < 4.5, `média de gols ${gols / 600}`);
});

teste("previsão de Poisson bate com a simulação", () => {
  const r = semente(7);
  const prev = M.previsao(cfg("PAL"), cfg("FLA"));
  assert.ok(Math.abs(prev.vitoria + prev.empate + prev.derrota - 1) < 1e-9);
  let v = 0;
  const n = 1500;
  for (let k = 0; k < n; k += 1) {
    const { partida } = M.simularPartida(cfg("PAL"), cfg("FLA"), r);
    if (partida.lados[0].gols > partida.lados[1].gols) v += 1;
  }
  assert.ok(Math.abs(v / n - prev.vitoria) < 0.06, `${v / n} x ${prev.vitoria}`);
});

teste("todo mata-mata tem vencedor e a disputa de pênaltis segue a regra", () => {
  const r = semente(99);
  let disputas = 0;
  for (let k = 0; k < 300; k += 1) {
    const { partida, disputa } = M.simularPartida(cfg("COR"), cfg("SPA"), r);
    assert.notEqual(M.vencedorDe(partida, disputa), null);
    if (!disputa) continue;
    disputas += 1;
    const [a, b] = disputa.cobrancas.map((l) => l.length);
    const [ga, gb] = M.golsDisputa(disputa);
    assert.notEqual(ga, gb);
    assert.ok(Math.abs(a - b) <= 1 && a >= 3 && b >= 3);
    if (a > 5 || b > 5) assert.equal(a, b, "morte súbita termina com o mesmo número de cobranças");
  }
  assert.ok(disputas > 20, `poucas disputas: ${disputas}`);
});

teste("no máximo cinco substituições e só com quem está no banco", () => {
  const p = M.criarPartida({ ...cfg("FLU"), controlado: true }, cfg("GRE"), semente(1));
  const lado = p.lados[0];
  assert.match(M.substituir(p, 0, lado.emCampo[1].jogador.id, lado.emCampo[2].jogador.id), /banco/);
  for (let k = 0; k < 5; k += 1) {
    assert.equal(M.substituir(p, 0, lado.emCampo[k + 1].jogador.id, lado.banco[0]), null);
  }
  assert.equal(lado.subs, 5);
  assert.notEqual(M.substituir(p, 0, lado.emCampo[7].jogador.id, lado.banco[0]), null);
});

teste("mudar formação e trocar posições no meio do jogo mantém os mesmos 11", () => {
  const p = M.criarPartida(cfg("BOT", { controlado: true }), cfg("CUI"), semente(7));
  for (let k = 0; k < 20; k++) M.avancar(p);
  const lado = p.lados[0];
  const antes = new Set(lado.emCampo.map((x) => x.jogador.id));
  M.mudarFormacao(p, 0, "3-5-2");
  assert.equal(lado.formacao, "3-5-2");
  assert.deepEqual(new Set(lado.emCampo.map((x) => x.jogador.id)), antes);
  const setores = E.setoresDaFormacao("3-5-2");
  assert.ok(lado.emCampo.every((x) => x.setor === setores[x.vaga]));
  assert.equal(lado.emCampo.find((x) => x.vaga === 0).jogador.setor, "GOL");
  const [a, b] = [lado.emCampo[3], lado.emCampo[9]];
  const [ja, jb] = [a.jogador.id, b.jogador.id];
  M.trocarPosicoes(p, 0, ja, jb);
  assert.equal(a.jogador.id, jb);
  assert.equal(b.jogador.id, ja);
  assert.equal(lado.subs, 0);
});

teste("cansaço derruba a força em campo", () => {
  const t = times.get("INT");
  const ids = E.escalarAutomatico(t, t.formacao);
  const setores = E.setoresDaFormacao(t.formacao);
  const emCampo = (energia) => ids.map((id, i) => ({ jogador: t.porId.get(id), setor: setores[i], energia }));
  assert.ok(E.forcasEmCampo(emCampo(100), t.formacao).ataque > E.forcasEmCampo(emCampo(40), t.formacao).ataque + 5);
});

let falhas = 0;
for (const [nome, fn] of testes) {
  try {
    fn();
    console.log(`ok - ${nome}`);
  } catch (erro) {
    falhas += 1;
    console.log(`FALHOU - ${nome}\n${erro.stack}`);
  }
}
process.exit(falhas ? 1 : 0);
