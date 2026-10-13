// Contrato com `/api/previsao/*` (backend/gestao_trafego/previsao/treinar.py e api/rotas_historico.py).

export interface MetricaDoHorizonte {
  horizonte_s: number;
  mae_lstm_veiculos: number;
  mae_persistencia_veiculos: number;
}

export interface MetricasDaPrevisao {
  fila_media_do_teste_veiculos: number;
  recuo_s: number;
  sementes_de_teste: number[];
  execucoes_de_treino: number;
  execucoes_de_teste: number;
  janelas_de_treino: number;
  janelas_de_teste: number;
  epocas: number;
  por_horizonte: (MetricaDoHorizonte & { melhoria_percentual: number })[];
  por_configuracao: Record<string, MetricaDoHorizonte[]>;
}

export interface PontoDaPrevisao {
  tempo_s: number;
  previsto: number;
  real: number;
}
