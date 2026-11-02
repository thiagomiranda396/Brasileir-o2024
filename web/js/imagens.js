// Escudos e fotos: miniaturas da Wikimedia Commons registradas no banco.
//
// Nenhuma imagem é copiada para o repositório e o site não procura imagens sozinho: o script
// scripts/buscar_fotos.py confirma cada jogador (Wikidata ou ficha da Wikipédia), guarda a URL da miniatura com
// autor e licença (core.escudo_clube e core.foto_jogador) e o JSON exportado traz só a URL.
// O navegador carrega a imagem da Wikimedia; os créditos ficam na página "Créditos das imagens".
// Sem imagem confirmada, ou sem rede, fica o distintivo com a sigla ou as iniciais.

export function iniciais(nome) {
  const partes = nome.split(/\s+/).filter(Boolean);
  return (partes[0][0] + (partes.length > 1 ? partes[partes.length - 1][0] : "")).toUpperCase();
}

function trocarPorImagem(el, url, alt) {
  const img = new Image();
  img.alt = alt;
  img.decoding = "async";
  img.referrerPolicy = "no-referrer";
  img.onload = () => {
    el.replaceChildren(img);
    el.classList.add("com-imagem");
  };
  img.src = url;
}

export function escudo(clube, classe = "") {
  const el = document.createElement("span");
  el.className = `escudo ${classe}`.trim();
  el.title = clube.nome;
  const sigla = document.createElement("span");
  sigla.className = "escudo-sigla";
  sigla.style.setProperty("--c1", clube.cor1);
  sigla.style.setProperty("--c2", clube.cor2);
  sigla.textContent = clube.id;
  el.append(sigla);
  if (clube.escudo) trocarPorImagem(el, clube.escudo, `Escudo do ${clube.nome}`);
  return el;
}

export function foto(jogador, clube, classe = "") {
  const el = document.createElement("span");
  el.className = `foto ${classe}`.trim();
  const ini = document.createElement("span");
  ini.className = "foto-iniciais";
  ini.textContent = iniciais(jogador.nome);
  el.append(ini);
  if (clube) el.style.borderColor = clube.cor1;
  if (jogador.foto) trocarPorImagem(el, jogador.foto, `Foto de ${jogador.nome}`);
  return el;
}
