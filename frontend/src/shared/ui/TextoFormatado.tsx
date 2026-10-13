import { Fragment, type ReactNode } from "react";
import { analisarMarkdown, type Segmento } from "../utils/markdownSimples";

function Inline({ segmentos }: { segmentos: Segmento[] }): ReactNode {
  return segmentos.map((s, i) =>
    s.negrito ? <strong key={i}>{s.texto}</strong> : s.codigo ? <code key={i}>{s.texto}</code> : <Fragment key={i}>{s.texto}</Fragment>,
  );
}

/** Mostra a resposta do assistente com um markdown mínimo (títulos, listas, negrito, código), sem HTML bruto. */
export function TextoFormatado({ texto }: { texto: string }) {
  return (
    <div className="texto-formatado">
      {analisarMarkdown(texto).map((bloco, i) => {
        switch (bloco.tipo) {
          case "titulo":
            return (
              <p key={i} className="texto-titulo">
                <Inline segmentos={bloco.segmentos} />
              </p>
            );
          case "paragrafo":
            return (
              <p key={i}>
                <Inline segmentos={bloco.segmentos} />
              </p>
            );
          case "regra":
            return <hr key={i} />;
          case "lista": {
            const Lista = bloco.ordenada ? "ol" : "ul";
            return (
              <Lista key={i}>
                {bloco.itens.map((item, j) => (
                  <li key={j}>
                    <Inline segmentos={item} />
                  </li>
                ))}
              </Lista>
            );
          }
        }
      })}
    </div>
  );
}
