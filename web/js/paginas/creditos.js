import { h, cabecalho, cartao, listaComMais } from "../ui.js";

const CHAVE_BUSCA = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function render(main, d) {
  main.append(cabecalho("Créditos das imagens",
    "Escudos e fotos não ficam guardados neste site: são carregados da Wikimedia. Fotos só com licença livre ou em domínio público; três escudos são de uso justo."));

  const escudos = d.creditos.filter((c) => c.tipo === "Escudo");
  const fotos = d.creditos.filter((c) => c.tipo === "Foto");
  const comFoto = fotos.length;
  const total = d.jogadores.size;

  main.append(cartao("Como as imagens foram escolhidas", null,
    h("p", {}, `${escudos.length} escudos e ${comFoto} fotos de jogadores (de ${total}). Cada foto só entra quando a Wikidata (ou, na falta do registro lá, a ficha do jogador na Wikipédia em inglês) confirma que a pessoa jogou naquele clube em 2024 e tem o mesmo nome; quem ficou sem confirmação aparece com a camisa do clube, sem um rosto inventado.`),
    h("p", { class: "mudo pequeno" }, "Escudos são marcas dos respectivos clubes e aparecem só para identificá-los; os marcados como \"Uso justo\" não têm licença livre e vêm da Wikipédia em português. Fotos de atletas seguem a licença indicada pelo autor na Wikimedia Commons.")));

  if (!d.creditos.length) {
    main.append(h("p", { class: "sem-dados" }, "Nenhuma imagem registrada ainda: rode scripts/buscar_fotos.py, a carga do banco e a exportação."));
    return;
  }

  const linha = (c) => h("li", {},
    h("strong", {}, c.nome), " · ",
    h("a", { href: c.pagina, rel: "noopener" }, c.arquivo),
    ` · Autor: ${c.autor || "não informado (domínio público)"} · Licença: `,
    c.licenca_url ? h("a", { href: c.licenca_url, rel: "noopener" }, c.licenca) : c.licenca);

  main.append(cartao(`Escudos (${escudos.length})`, null, h("ul", { class: "creditos" }, escudos.map(linha))));

  // Lista longa: as primeiras 20 e "Mostrar mais"; o filtro procura em todas.
  const lista = h("div", {});
  const desenhar = (filtro) => {
    const alvo = CHAVE_BUSCA(filtro.trim());
    const achadas = fotos.filter((c) => !alvo || CHAVE_BUSCA(c.nome).includes(alvo));
    lista.replaceChildren(achadas.length
      ? listaComMais(achadas, linha, { inicial: 20, classe: "creditos", rotulo: "fotos" })
      : h("p", { class: "sem-dados" }, "Nenhuma foto com esse nome."));
  };
  const busca = h("input", { type: "search", placeholder: "Filtrar por jogador…", "aria-label": "Filtrar fotos por jogador",
    oninput: (ev) => desenhar(ev.target.value) });
  desenhar("");
  main.append(cartao(`Fotos de jogadores (${comFoto})`, null, busca, lista));
}
