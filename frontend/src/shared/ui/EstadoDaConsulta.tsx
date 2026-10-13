import type { UseQueryResult } from "@tanstack/react-query";
import { AlertTriangle, Inbox } from "lucide-react";
import type { ReactNode } from "react";
import { mensagemDeErro } from "../utils/mensagemDeErro";

interface Props<T> {
  consulta: UseQueryResult<T>;
  /** Decide se o resultado conta como «vazio» (lista vazia não é erro). */
  vazio?: (dados: T) => boolean;
  mensagemVazia?: string;
  alturaDoEsqueleto?: number;
  children: (dados: T) => ReactNode;
}

/** Os quatro estados de uma chamada à API: a carregar (esqueleto), erro, vazio e sucesso. */
export function EstadoDaConsulta<T>({ consulta, vazio, mensagemVazia = "Ainda não há dados.", alturaDoEsqueleto = 160, children }: Props<T>) {
  if (consulta.isPending) {
    return <div className="esqueleto" style={{ height: alturaDoEsqueleto }} role="status" aria-label="A carregar" />;
  }
  if (consulta.isError) {
    return (
      <div className="estado-mensagem erro" role="alert">
        <AlertTriangle size={20} aria-hidden />
        <div>
          <strong>Não foi possível carregar os dados</strong>
          {mensagemDeErro(consulta.error)}
        </div>
      </div>
    );
  }
  if (vazio?.(consulta.data)) {
    return (
      <div className="estado-mensagem">
        <Inbox size={20} aria-hidden />
        <div>{mensagemVazia}</div>
      </div>
    );
  }
  return <>{children(consulta.data)}</>;
}
