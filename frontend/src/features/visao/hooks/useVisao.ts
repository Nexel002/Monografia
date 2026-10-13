import { useQuery } from "@tanstack/react-query";
import { obterPastas, obterResumo, obterVideos } from "../api/visaoApi";

export const usePastas = () => useQuery({ queryKey: ["visao", "pastas"], queryFn: obterPastas });

export const useResumoDeVisao = (pasta: string | null) =>
  useQuery({ queryKey: ["visao", "resumo", pasta], queryFn: () => obterResumo(pasta!), enabled: pasta !== null });

export const useVideos = () => useQuery({ queryKey: ["visao", "videos"], queryFn: obterVideos });
