import { useMutation, useQuery } from "@tanstack/react-query";
import { obterEstadoDoAssistente, obterRelatorio, perguntar } from "../api/assistenteApi";
import type { MensagemDoHistorico } from "../types/assistente";

export const useEstadoDoAssistente = () => useQuery({ queryKey: ["assistente", "estado"], queryFn: obterEstadoDoAssistente });

export const usePergunta = () =>
  useMutation({ mutationFn: ({ pergunta, historico }: { pergunta: string; historico: MensagemDoHistorico[] }) => perguntar(pergunta, historico) });

export const useRelatorio = () => useMutation({ mutationFn: obterRelatorio });
