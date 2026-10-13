import { obter } from "../../../shared/api/cliente";
import type { AmostraDaSerie, Execucao, LinhaDaComparacao } from "../types/resultados";

export const obterComparacao = (incidente: boolean) => obter<LinhaDaComparacao[]>("/api/comparacao", { incidente, escala: 1 });
export const obterExecucoes = () => obter<Execucao[]>("/api/execucoes");
export const obterSerie = (execucaoId: number) => obter<AmostraDaSerie[]>(`/api/execucoes/${execucaoId}/serie`);
