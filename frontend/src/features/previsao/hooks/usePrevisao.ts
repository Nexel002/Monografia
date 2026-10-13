import { useQuery } from "@tanstack/react-query";
import { obterMetricas, obterPrevisao } from "../api/previsaoApi";

export const useMetricas = () => useQuery({ queryKey: ["previsao", "metricas"], queryFn: obterMetricas });

export const usePrevisao = (execucaoId: number | null, horizonteS: number) =>
  useQuery({
    queryKey: ["previsao", execucaoId, horizonteS],
    queryFn: () => obterPrevisao(execucaoId!, horizonteS),
    enabled: execucaoId !== null,
  });
