import { enviar, enviarParaBlob, obter } from "../../../shared/api/cliente";
import type { EstadoDoAssistente, MensagemDoHistorico, RespostaDoAssistente } from "../types/assistente";

export const obterEstadoDoAssistente = () => obter<EstadoDoAssistente>("/api/assistente/estado");
export const obterRelatorio = () => obter<RespostaDoAssistente>("/api/assistente/relatorio");
export const perguntar = (pergunta: string, historico: MensagemDoHistorico[]) =>
  enviar<RespostaDoAssistente>("/api/assistente/perguntar", { pergunta, historico });
/** Áudio da voz do servidor, ou null se não houver (o browser fala por si). */
export const sintetizarVoz = (texto: string) => enviarParaBlob("/api/assistente/voz", { texto });
