// Tipos do contrato com a API (backend/gestao_trafego/api/rotas_historico.py). Têm de bater certo.

export interface LinhaDaComparacao {
  configuracao: string;
  sementes: number;
  espera_media_s: number;
  /** pode ser null se só houver uma semente */
  espera_desvio_s: number | null;
  fila_media_veiculos: number;
  velocidade_media_ms: number;
  teleportes: number;
}

export interface Execucao {
  id: number;
  nome: string;
  configuracao: string;
  semente: number;
  escala: number;
  incidente: boolean;
  espera_media_s: number;
  fila_media_veiculos: number;
  velocidade_media_ms: number;
  teleportes: number;
  veiculos_concluidos: number;
}

export interface AmostraDaSerie {
  tempo_s: number;
  veiculos_na_rede: number;
  veiculos_parados: number;
  velocidade_media_ms: number;
}
