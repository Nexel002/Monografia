import { obter } from "../../../shared/api/cliente";
import { API_URL } from "../../../shared/config/api";
import type { VideoOriginal } from "../types/aoVivo";
import type { PastaDeVisao, ResumoDeVisao } from "../types/visao";

export const obterPastas = () => obter<PastaDeVisao[]>("/api/visao");
export const obterResumo = (pasta: string) => obter<ResumoDeVisao>(`/api/visao/${encodeURIComponent(pasta)}/resumo`);
export const enderecoDoVideo = (pasta: string) => `${API_URL}/api/visao/${encodeURIComponent(pasta)}/video`;

export const obterVideos = () => obter<VideoOriginal[]>("/api/visao/videos");
export const enderecoDoVideoOriginal = (nome: string) => `${API_URL}/api/visao/videos/${encodeURIComponent(nome)}`;
