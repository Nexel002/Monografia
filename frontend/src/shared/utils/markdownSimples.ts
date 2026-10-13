// Um analisador de markdown mínimo para as respostas do assistente: títulos, listas, negrito, código e linha.
// Devolve estrutura de dados (e não HTML): quem desenha usa elementos React, que escapam o texto. Assim uma resposta
// do modelo nunca consegue injectar HTML na página.

export interface Segmento {
  texto: string;
  negrito?: boolean;
  codigo?: boolean;
}

export type Bloco =
  | { tipo: "titulo"; nivel: number; segmentos: Segmento[] }
  | { tipo: "paragrafo"; segmentos: Segmento[] }
  | { tipo: "lista"; ordenada: boolean; itens: Segmento[][] }
  | { tipo: "regra" };

export function analisarInline(texto: string): Segmento[] {
  return texto
    .split(/(\*\*[^*]+\*\*|`[^`]+`)/)
    .filter(Boolean)
    .map((parte): Segmento => {
      if (parte.startsWith("**") && parte.endsWith("**") && parte.length > 4) return { texto: parte.slice(2, -2), negrito: true };
      if (parte.startsWith("`") && parte.endsWith("`") && parte.length > 2) return { texto: parte.slice(1, -1), codigo: true };
      return { texto: parte };
    });
}

export function analisarMarkdown(texto: string): Bloco[] {
  const blocos: Bloco[] = [];
  let paragrafo: string[] = [];
  let lista: { ordenada: boolean; itens: Segmento[][] } | null = null;

  const fecharParagrafo = () => {
    if (paragrafo.length) blocos.push({ tipo: "paragrafo", segmentos: analisarInline(paragrafo.join(" ")) });
    paragrafo = [];
  };
  const fecharLista = () => {
    if (lista) blocos.push({ tipo: "lista", ...lista });
    lista = null;
  };

  for (const linha of texto.split("\n")) {
    const limpa = linha.trim();
    const titulo = limpa.match(/^(#{1,6})\s+(.*)$/);
    const item = linha.match(/^\s*([*-]|\d+\.)\s+(.*)$/);
    if (!limpa) {
      fecharParagrafo();
      fecharLista();
    } else if (/^(-{3,}|\*{3,})$/.test(limpa)) {
      fecharParagrafo();
      fecharLista();
      blocos.push({ tipo: "regra" });
    } else if (titulo) {
      fecharParagrafo();
      fecharLista();
      blocos.push({ tipo: "titulo", nivel: titulo[1].length, segmentos: analisarInline(titulo[2]) });
    } else if (item) {
      fecharParagrafo();
      const ordenada = /\d/.test(item[1]);
      if (lista && lista.ordenada !== ordenada) fecharLista();
      lista ??= { ordenada, itens: [] };
      lista.itens.push(analisarInline(item[2]));
    } else {
      fecharLista();
      paragrafo.push(limpa);
    }
  }
  fecharParagrafo();
  fecharLista();
  return blocos;
}
