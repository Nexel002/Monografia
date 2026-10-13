import { obter } from "../../../shared/api/cliente";
import { API_URL } from "../../../shared/config/api";
import type { PastaDeVisao, ResumoDeVisao } from "../types/visao";

export const obterPastas = () => obter<PastaDeVisao[]>("/api/visao");
export const obterResumo = (pasta: string) => obter<ResumoDeVisao>(`/api/visao/${encodeURIComponent(pasta)}/resumo`);
export const enderecoDoVideo = (pasta: string) => `${API_URL}/api/visao/${encodeURIComponent(pasta)}/video`;
