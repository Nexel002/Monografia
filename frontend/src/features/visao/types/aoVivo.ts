// Contrato do WebSocket `/ws/visao` (backend/gestao_trafego/api/visao_ao_vivo.py). Têm de bater certo.

/** [id, x1, y1, x2, y2, tipo, contado] em píxeis da resolução de trabalho (a de `InfoDaVisao`). */
export type VeiculoDetectado = [id: number, x1: number, y1: number, x2: number, y2: number, tipo: string, contado: 0 | 1];

export interface TotaisDaContagem {
  total: number;
  por_tipo: Record<string, number>;
  por_sentido: Record<string, number>;
}

export interface InfoDaVisao {
  largura: number;
  altura: number;
  fps: number;
  duracao_s: number;
  /** até que segundo se analisa (o limite pedido, ou a duração do vídeo) */
  ate_s: number;
  /** x1, y1, x2, y2 da linha de contagem, em píxeis da resolução de trabalho */
  linha: [number, number, number, number];
  modelo: string;
  tamanho_imagem: number;
}

export interface MensagemDeDeteccoes {
  tipo: "deteccoes";
  indice: number;
  t_video: number;
  veiculos: VeiculoDetectado[];
  totais: TotaisDaContagem;
  analises_por_s: number;
  latencia_media_ms: number;
}

export interface ResumoFinal extends TotaisDaContagem {
  analises: number;
  fotogramas_lidos: number;
  latencia_media_ms: number;
}

export type MensagemDaVisao =
  | { tipo: "a_preparar" }
  | ({ tipo: "pronto" } & InfoDaVisao)
  | MensagemDeDeteccoes
  | { tipo: "fim"; resumo: ResumoFinal }
  | { tipo: "erro"; mensagem: string };

export interface VideoOriginal {
  nome: string;
  tamanho_mb: number;
}

export interface ParametrosDaVisaoAoVivo {
  video: string;
  /** limita a análise aos primeiros N segundos; null = o vídeo todo */
  segundos: number | null;
  imgsz: number;
}
