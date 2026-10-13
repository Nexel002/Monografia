// Contrato com `/api/assistente/*` (backend/gestao_trafego/api/rotas_assistente.py). Têm de bater certo.

export type Papel = "utilizador" | "assistente";

export interface MensagemDoHistorico {
  papel: Papel;
  texto: string;
}

export interface RespostaDoAssistente {
  texto: string;
  /** «gemini» = modelo de linguagem; «seguranca» = respostas sem modelo (sem chave ou sem rede) */
  modo: "gemini" | "seguranca";
  ferramentas_usadas: string[];
  aviso: string | null;
}

export interface EstadoDoAssistente {
  gemini_configurado: boolean;
  voz_do_servidor: boolean;
  perguntas_sugeridas: string[];
}

/** Uma mensagem no ecrã: as do utilizador só têm texto; as do assistente trazem o modo e as ferramentas. */
export interface MensagemNoEcra extends MensagemDoHistorico {
  id: number;
  resposta?: RespostaDoAssistente;
}
