import type { ReactNode } from "react";

interface Props {
  titulo?: string;
  accao?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Cartao({ titulo, accao, children, className }: Props) {
  return (
    <section className={`cartao${className ? ` ${className}` : ""}`}>
      {(titulo || accao) && (
        <header>
          {titulo && <h2>{titulo}</h2>}
          {accao}
        </header>
      )}
      {children}
    </section>
  );
}
