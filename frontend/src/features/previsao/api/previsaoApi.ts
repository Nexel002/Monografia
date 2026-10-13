import { obter } from "../../../shared/api/cliente";
import type { MetricasDaPrevisao, PontoDaPrevisao } from "../types/previsao";

export const obterMetricas = () => obter<MetricasDaPrevisao>("/api/previsao/metricas");
export const obterPrevisao = (execucaoId: number, horizonteS: number) =>
  obter<PontoDaPrevisao[]>(`/api/previsao/${execucaoId}`, { horizonte_s: horizonteS });
