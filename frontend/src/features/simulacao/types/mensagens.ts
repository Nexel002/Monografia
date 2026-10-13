// Contrato do WebSocket `/ws/simulacao` (backend/gestao_trafego/api/ao_vivo.py). Têm de bater certo.

/** [id, x, y, ângulo (graus, no sentido horário a partir do norte), tipo, parado] */
export type VeiculoMsg = [id: string, x: number, y: number, angulo: number, tipo: number, parado: 0 | 1];

export interface IndicadoresMsg {
  na_rede: number;
  parados: number;
  velocidade_media_ms: number;
  chegados: number;
  espera_media_s: number;
}

export interface LadoMsg {
  v: VeiculoMsg[];
  /** estado de cada sinal por semáforo: G/g verde, y amarelo, r vermelho */
  s: Record<string, string>;
  k: IndicadoresMsg;
}

export type Lado = "esquerda" | "direita";

export type MensagemDoServidor =
  | { tipo: "inicio"; configuracoes: Record<Lado, string>; semente: number; incidente: boolean }
  | ({ tipo: "estado"; t: number } & Record<Lado, LadoMsg>)
  | { tipo: "fim"; t: number }
  | { tipo: "erro"; mensagem: string };

export const TIPO_CARRO = 0;
export const TIPO_CHAPA = 1;
export const TIPO_MOTA = 2;
export const TIPO_CAMIAO = 3;
export const TIPO_AVARIADO = 4;

export interface ParametrosDaSimulacao {
  semente: number;
  velocidade: number;
  incidente: boolean;
  esquerda: string;
  direita: string;
}

export interface Rede {
  limites: { x_min: number; y_min: number; x_max: number; y_max: number };
  ruas: { id: string; nome: string; faixas: number; pontos: [number, number][] }[];
  semaforos: { id: string; centro: [number, number] | null; sinais: [number, number][] }[];
}
