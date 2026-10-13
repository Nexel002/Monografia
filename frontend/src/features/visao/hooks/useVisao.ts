import { useQuery } from "@tanstack/react-query";
import { obterPastas, obterResumo } from "../api/visaoApi";

export const usePastas = () => useQuery({ queryKey: ["visao", "pastas"], queryFn: obterPastas });

export const useResumoDeVisao = (pasta: string | null) =>
  useQuery({ queryKey: ["visao", "resumo", pasta], queryFn: () => obterResumo(pasta!), enabled: pasta !== null });
