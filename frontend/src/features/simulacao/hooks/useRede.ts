import { useQuery } from "@tanstack/react-query";
import { obterRede } from "../api/simulacaoApi";

// A geometria da rede nunca muda durante a sessão: guarda-se para sempre e não se volta a pedir.
export const useRede = () => useQuery({ queryKey: ["rede"], queryFn: obterRede, staleTime: Infinity });
