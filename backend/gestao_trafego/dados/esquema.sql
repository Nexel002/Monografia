-- Esquema do protótipo. Corre-se inteiro de cada vez que a aplicação liga (tudo é IF NOT EXISTS),
-- por isso não há migrações: uma alteração de colunas faz-se com uma tabela nova ou recriando a base.

CREATE TABLE IF NOT EXISTS execucao (
    id SERIAL PRIMARY KEY,
    nome TEXT UNIQUE NOT NULL,            -- nome da pasta de resultados; é a chave natural
    configuracao TEXT NOT NULL,           -- fixo | local | local+vias | coordenado | coordenado+vias
    cenario TEXT NOT NULL,
    semente INTEGER NOT NULL,
    escala REAL NOT NULL,
    incidente BOOLEAN NOT NULL,
    vias_alternativas BOOLEAN NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    tempo_simulado_s INTEGER NOT NULL,
    veiculos_concluidos INTEGER NOT NULL,
    veiculos_nao_concluidos INTEGER NOT NULL,
    espera_media_s DOUBLE PRECISION NOT NULL,
    perda_de_tempo_media_s DOUBLE PRECISION NOT NULL,
    duracao_viagem_media_s DOUBLE PRECISION NOT NULL,
    fila_media_veiculos DOUBLE PRECISION NOT NULL,
    fila_maxima_veiculos INTEGER NOT NULL,
    velocidade_media_ms DOUBLE PRECISION NOT NULL,
    teleportes INTEGER NOT NULL,
    colisoes INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS amostra (
    execucao_id INTEGER NOT NULL REFERENCES execucao(id) ON DELETE CASCADE,
    tempo_s INTEGER NOT NULL,
    veiculos_na_rede INTEGER NOT NULL,
    veiculos_parados INTEGER NOT NULL,
    velocidade_media_ms DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (execucao_id, tempo_s)
);

-- Contagens que a câmara (visão computacional) entrega ao sistema, por janela de tempo.
CREATE TABLE IF NOT EXISTS contagem_via (
    id SERIAL PRIMARY KEY,
    origem TEXT NOT NULL,                 -- nome do vídeo
    via TEXT NOT NULL,
    inicio_s DOUBLE PRECISION NOT NULL,
    fim_s DOUBLE PRECISION NOT NULL,
    por_tipo JSONB NOT NULL,
    total INTEGER NOT NULL,
    fluxo_veiculos_por_hora DOUBLE PRECISION NOT NULL,
    fila_media_veiculos DOUBLE PRECISION NOT NULL,
    UNIQUE (origem, via, inicio_s)
);

-- Previsão do LSTM contra o valor real, para o dashboard e para a avaliação.
CREATE TABLE IF NOT EXISTS previsao (
    id SERIAL PRIMARY KEY,
    modelo TEXT NOT NULL,
    execucao_id INTEGER NOT NULL REFERENCES execucao(id) ON DELETE CASCADE,
    horizonte_s INTEGER NOT NULL,
    tempo_s INTEGER NOT NULL,             -- instante a que a previsão diz respeito
    previsto DOUBLE PRECISION NOT NULL,
    real DOUBLE PRECISION NOT NULL,
    UNIQUE (modelo, execucao_id, horizonte_s, tempo_s)
);

CREATE INDEX IF NOT EXISTS idx_execucao_configuracao ON execucao (configuracao, incidente, escala);
