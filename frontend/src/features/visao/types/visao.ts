// Contrato com `/api/visao/*` (backend/gestao_trafego/api/rotas_visao.py e visao/contar.py).

export interface PastaDeVisao {
  pasta: string;
  tem_video: boolean;
  total: number | null;
  modelo: string | null;
  tamanho_imagem: number | null;
  fps_de_processamento: number | null;
}

export interface JanelaDeContagem {
  via: string;
  inicio_s: number;
  fim_s: number;
  por_tipo: Record<string, number>;
  total: number;
  fluxo_veiculos_por_hora: number;
  fila_media_veiculos: number;
}

export interface ResumoDeVisao {
  modo?: string;
  video: string;
  modelo: string;
  tamanho_imagem?: number;
  fps_de_processamento?: number;
  fotogramas_processados?: number;
  duracao_processada_s?: number;
  total: number;
  por_tipo: Record<string, number>;
  por_sentido: Record<string, number>;
  /** só existe em corridas posteriores à agregação por janelas */
  janelas?: JanelaDeContagem[];
}

export const TIPOS_DE_VEICULO = ["carro", "mota", "autocarro", "camiao"] as const;
export const ROTULO_DO_TIPO: Record<string, string> = { carro: "Carros", mota: "Motas", autocarro: "Autocarros", camiao: "Camiões" };
