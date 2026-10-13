import { useQueries, useQuery } from "@tanstack/react-query";
import { obterComparacao, obterExecucoes, obterSerie } from "../api/resultadosApi";

export const useComparacao = (incidente: boolean, escala: number) =>
  useQuery({ queryKey: ["comparacao", incidente, escala], queryFn: () => obterComparacao(incidente, escala) });

export const useExecucoes = () => useQuery({ queryKey: ["execucoes"], queryFn: obterExecucoes });

/** Uma série por execução pedida (uma por configuração da mesma semente). */
export const useSeries = (ids: number[]) =>
  useQueries({ queries: ids.map((id) => ({ queryKey: ["serie", id], queryFn: () => obterSerie(id), staleTime: Infinity })) });
