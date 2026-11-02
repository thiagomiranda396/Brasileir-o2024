// Ponto de entrada: carrega os dados, aplica o tema e faz o roteamento por hash (#/pagina/param).
import { carregarDados } from "./dados.js";
import { esconderTooltip } from "./graficos.js";
import { h, lerPreferencia, gravarPreferencia, faixaTitulo } from "./ui.js";
import * as visaoGeral from "./paginas/visao_geral.js";
import * as classificacao from "./paginas/classificacao.js";
import * as clubes from "./paginas/clubes.js";
import * as jogadores from "./paginas/jogadores.js";
import * as partidas from "./paginas/partidas.js";
import * as jogos from "./paginas/jogos.js";
import * as creditos from "./paginas/creditos.js";

const ROTAS = { "": visaoGeral, classificacao, clubes, jogadores, partidas, jogos, creditos };
const TITULOS = {
  "": "Visão geral", classificacao: "Classificação", clubes: "Clubes", jogadores: "Jogadores",
  partidas: "Partidas", jogos: "Prancheta 2024", creditos: "Créditos das imagens",
};

// Tema: segue o sistema; o botão grava a escolha do visitante.
const tema = lerPreferencia("br24-tema", null);
if (tema) document.documentElement.dataset.theme = tema;
document.querySelector(".botao-tema").addEventListener("click", () => {
  const atual = document.documentElement.dataset.theme
    || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const novo = atual === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = novo;
  gravarPreferencia("br24-tema", novo);
  // As cores do clube nos gráficos dependem do fundo: redesenha a página do clube no tema novo.
  if (dados && rotaAtual().pagina === "clubes") renderizar();
});

// Filtros abertos no computador; no celular ficam recolhidos atrás do botão "Filtros".
const painelFiltros = document.querySelector(".painel-filtros");
const telaLarga = matchMedia("(min-width: 900px)");
const ajustarPainel = () => { painelFiltros.open = telaLarga.matches; };
ajustarPainel();
telaLarga.addEventListener("change", ajustarPainel);

const main = document.querySelector("main");

function rotaAtual() {
  // Aceita "#/pagina/param" e "#pagina--param" (formato da prévia publicada como Artifact).
  const [pagina = "", ...params] = location.hash.replace(/^#\/?/, "").split(/\/|--/).map(decodeURIComponent);
  return { pagina: pagina in ROTAS ? pagina : "", params };
}

let dados = null;

function renderizar() {
  esconderTooltip();
  const { pagina, params } = rotaAtual();
  for (const a of document.querySelectorAll(".menu a")) {
    if (a.dataset.rota === pagina) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  document.title = `${TITULOS[pagina]} · Brasileirão 2024`;
  main.replaceChildren();
  // Cada página monta o próprio título e os próprios filtros.
  faixaTitulo({ titulo: TITULOS[pagina] });
  document.getElementById("filtros").replaceChildren();
  painelFiltros.hidden = true;
  try {
    ROTAS[pagina].render(main, dados, params);
  } catch (erro) {
    console.error(erro);
    main.append(h("p", { class: "aviso" }, `Erro ao montar a página: ${erro.message}`));
  }
}

let ultimaPagina = null;
window.addEventListener("hashchange", () => {
  const { pagina } = rotaAtual();
  renderizar();
  if (pagina !== ultimaPagina) {
    window.scrollTo({ top: 0 });
    main.focus({ preventScroll: true });
  }
  ultimaPagina = pagina;
});

carregarDados()
  .then((d) => {
    dados = d;
    ultimaPagina = rotaAtual().pagina;
    renderizar();
  })
  .catch((erro) => {
    main.replaceChildren(h("p", { class: "aviso" },
      `Não foi possível carregar os dados (${erro.message}). Se abriu o arquivo direto do disco, `
      + "sirva a pasta web/ por HTTP (ex.: python -m http.server -d web)."));
  });
