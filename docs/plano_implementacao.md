# Plano de Implementação — Protótipo da Monografia

Sistema integrado com IA para apoio à gestão de tráfego rodoviário na Cidade e Província de Maputo.
Este é o **único** documento de planeamento do protótipo. A monografia vive em `docs/monografia/`.

**Prazo:** 2 semanas a contar de 10/10/2026. **Nível:** licenciatura. **Objectivo:** protótipo funcional
e demonstrável na defesa, que prove que a ideia é viável — não um sistema de produção.

---

## 1. Fase em curso

**Fase 4 — Previsão, dados e API (dias 9–11)**

*4a/4b — feitas (ver Histórico):* PostgreSQL embebido, importação dos resultados, LSTM treinado e avaliado.

*4c — API (por fazer):*
- [ ] Refactor: extrair de `executar.py` uma `SessaoDeSimulacao` que avança passo a passo (hoje o ciclo
      está dentro de uma função só), para a mesma lógica servir a corrida em lote e a simulação ao vivo
- [ ] FastAPI: rotas de histórico (execuções, série, comparação por configuração, previsões, contagens da visão)
- [ ] WebSocket: simulação ao vivo com **dois cenários lado a lado** (tempo fixo contra coordenado + vias),
      mesma semente; envia posições dos veículos, estado dos semáforos e KPIs
- [ ] Rota da geometria da rede (ruas e semáforos) e do vídeo anotado
- [ ] Testes da API

*4d — Dashboard React (por fazer):*
- [ ] Vite + React + TypeScript; mapa ao vivo lado a lado, KPIs, gráficos de resultados e previsão
      contra real, vídeo anotado com contagens; tema escuro de sala de controlo, a funcionar em ecrã grande

**Como verificar:** `cd backend && uv run python -m gestao_trafego.dados.importar` e
`uv run python -m gestao_trafego.previsao.treinar` (já existem); a API e o dashboard ficam por definir.

---

## 1.1 Histórico de entregas

### Fase 4a/4b — Base de dados e previsão (13/10/2026)
`dados/` (PostgreSQL) e `previsao/` (LSTM). Testes: 17 novos; total 70 (`uv run pytest`).

- **PostgreSQL embebido** (`pgserver`, sem instalação nem administrador; dados em `dados/postgres/`, fora do
  Git). Com `DATABASE_URL` definida usa-se um servidor próprio. Esquema em `dados/esquema.sql`: `execucao`,
  `amostra`, `contagem_via`, `previsao`. `python -m gestao_trafego.dados.importar` importa as pastas de
  `dados/resultados/` (idempotente; ignora os ensaios curtos `_limN`): 49 execuções e as janelas de contagem.
- **Comparação por configuração** (`repositorio.comparar_configuracoes`): só usa as sementes comuns a todas
  as configurações, senão se compararia o acaso das sementes.
- **LSTM** (`previsao/`): janelas de 5 min de [parados, na rede, velocidade] → veículos parados daqui a 1, 3
  e 5 min. Treino em 36 execuções e teste em 13, **divididas por semente** (as sementes 5 e 13 só no
  teste) para não avaliar em tráfego já visto. `python -m gestao_trafego.previsao.treinar`.

**Resultado (erro absoluto médio em veículos parados; fila média no teste 53):**

| Horizonte | LSTM | Persistência | Melhoria |
|---|---|---|---|
| 60 s | 13,2 | 21,5 | +39 % |
| 180 s | 17,1 | 18,9 | +10 % |
| 300 s | 19,9 | 25,7 | +23 % |

**Leitura honesta:** a melhoria vem sobretudo do **tempo fixo** (60 s: 11,1 contra 34,9; 300 s: 17,4 contra
39,2), onde a fila segue o ciclo periódico dos semáforos e a persistência erra a fase. Sob controlo
adaptativo o ganho é pequeno aos 60 s (≈15 %: local 15,4 contra 18,0; coordenado+vias 12,0 contra 16,1),
quase nulo aos 180 s e **aos 300 s o LSTM não bate a persistência no controlo local** (23,3 contra 23,0).
Apoia a H2 só de forma parcial e a curto prazo. Erro de 12 a 20 veículos sobre uma fila média de 53 é
elevado: o alvo (parados na rede inteira, de 10 em 10 s) é ruidoso.

**Desvios e limitações:**
- O LSTM prevê a fila agregada da rede, não a de cada faixa: o `serie.csv` só guarda totais. Previsão por
  faixa pediria registar mais na simulação.
- Python do projecto fixado em **3.12** (`backend/.python-version`): o `pgserver` só tem *wheels* para
  3.12 e o `uv` escolhia a 3.14.
- Variável nova: `DATABASE_URL` (opcional; sem ela usa-se o PostgreSQL embebido). Em `backend/.env.example`.

### Fase 3 — Visão: contagem de veículos por vídeo (12/10/2026)
Detecção e contagem de veículos em vídeo (`backend/gestao_trafego/visao/`): `contagem.py` (contagem por
linha, pura), `detector.py` (YOLOv8n + ByteTrack do `ultralytics`), `fila.py` (fila parada e agregação por
janela em `ContagemPorVia`), `extrapolar.py` e `ao_vivo.py` (janela à velocidade real), `anotar.py`,
`contar.py` (comando). Testes: 25 novos (`uv run pytest`).

- Offline (todos os fotogramas, vídeo anotado): `uv run python -m gestao_trafego.visao.contar --video ../dados/videos/<ficheiro>.mp4`
- Ao vivo (janela, `q` sai, espaço pausa): o mesmo comando com `--ao-vivo`
- Vídeo: `transito_autoestrada_pexels_2103099.mp4` (Pexels, autoestrada, 60 s, 1080p, 30 fps) em `dados/videos/` (fora do Git)

**Origem e licença:** a lógica de contagem foi escrita de raiz. O repositório indicado
(`anselmonhamage/automatic-number-plate-recognition-python-yolov8`, cópia de um tutorial de ANPR) **não
tem contagem por linha**: só detecção COCO + SORT + matrículas (modelo de matrículas fora do repositório).
Do áudio do autor (09/10/2026, transcrito localmente com Whisper) aplicou-se: ponto de contagem na **base**
da caixa e não no centro; contar os dois sentidos; verde = contado, amarelo = por contar; linha genérica
em fracções da imagem. O repositório é GPL-3.0 e o `ultralytics` AGPL-3.0: nenhum código foi copiado.

**Resultados no vídeo (mesmo vídeo, 3 modos; total contado):**

| Modo | Imagem YOLO | Velocidade | Total |
|---|---|---|---|
| Todos os fotogramas | 960 | 1,7 fotogramas/s | 54 |
| Todos os fotogramas | 480 | 6,9 fotogramas/s | 61 |
| Ao vivo (vídeo a 30 fps, análise em paralelo) | 480 | 4,5 análises/s | 41 |
| Ao vivo, 1.ª versão (desenhava a 1080p) | 640 | 1,0 análises/s | 25 |

**Leitura honesta:**
- **A precisão não está medida.** 54 e 61 diferem 13 % só por mudar a resolução da imagem; sem contagem
  manual não se sabe qual está certo. Contagem de referência a obter: carros que cruzam a linha nos
  primeiros 30 s (o sistema, a 960, contou 26).
- O modo ao vivo conta **menos** (41 contra 61 com o mesmo modelo): com poucas análises por segundo o
  seguimento perde a identidade de alguns veículos. A causa foi confirmada por exclusão (imagem 480 com
  todos os fotogramas dá 61). **A contagem oficial deve vir do modo fotograma-a-fotograma**; o ao vivo
  serve para mostrar o algoritmo a trabalhar.
- A 1.ª versão ao vivo tinha o detector a 1 análise/s (medido 6/s isolado) porque desenhar a 1080p
  consumia os 4 núcleos; reduzir o vídeo a 960 de largura e usar imagem 480 levou-o a 4,5/s.
- O vídeo é de **autoestrada**, não de um cruzamento de Maputo; o próprio autor do tutorial diz que não é
  bom para visão computacional. Substituível pondo outro ficheiro em `dados/videos/`.
- Matrículas (ANPR): **não implementadas** (modelo de matrículas indisponível; não é necessário ao controlo).
  Fica como trabalho futuro na monografia.

### Fase 2b — Coordenação, incidente e vias alternativas (11/10/2026)
Camada 2 (`controlo/coordenador/anti_bloqueio.py`), cenário `coordenado`, incidente que corta a Av. 24
de Julho (`simulacao/eventos.py`) e recomendação de vias alternativas (`simulacao/rotas_alternativas.py`).
Comparação em lote: `uv run python scripts/comparar_cenarios.py --incidente` e
`uv run python scripts/resumir_comparacao.py <tabelas>`. Testes: 26 (`uv run pytest`).

**O que a camada 2 faz:** vigia a ocupação das faixas; quando uma faixa de saída enche (≥ 60 %, com
histerese até 35 %) manda ao cruzamento que a alimenta *não lhe mandar mais carros* (fases cujas saídas
estão todas vedadas deixam de ser candidatas) e propaga o bloqueio a montante (uma faixa a encher cuja
saída está toda bloqueada também conta). Válvula de alívio: vedação máxima de 45 s, depois liberta 20 s.

**Resultado — hora de ponta + via cortada 10 min (espera média em segundos; 8 sementes: 42, 7, 13, 1–5):**

| Configuração | Espera média | Desvio | Variação vs fixo | Melhor que fixo | Teleportes (soma) |
|---|---|---|---|---|---|
| Tempo fixo | 135,3 | 30,5 | — | — | 187 |
| Local (Max-Pressure) | 102,8 | 26,2 | −24 % | 7/8 | 109 |
| Coordenado (local + camada 2) | 109,5 | 36,6 | −19 % | 6/8 | 152 |
| Local + vias alternativas | 78,7 | 10,6 | −42 % | 8/8 | 52 |
| **Coordenado + vias alternativas** | **76,1** | 7,0 | **−44 %** | 8/8 | **31** |

**Leitura honesta:**
- O ganho vem sobretudo do **controlo local adaptativo** (−24 %) e das **vias alternativas** (mais ~18 pontos,
  50 % dos condutores a seguir a recomendação). Estão em linha com a literatura.
- A **camada 2 anti-bloqueio sozinha não melhora o local** (−19 % contra −24 %, e piora na semente 7). Com
  vias alternativas fica ligeiramente melhor (−44 % contra −42 %) e mais estável (desvio 7,0 contra 10,6;
  31 teleportes contra 52), mas essa diferença é pequena para 8 sementes e não deve ser vendida como prova.
- Sem incidente, a camada 2 **nunca chegou a actuar** (resultados idênticos ao local): nem com a procura
  a dobrar uma faixa de saída passa dos 52 % de ocupação. Nesta rede, o *spillback* só aparece com via cortada.
- Com a procura a dobrar (`--escala 2`) todas as configurações bloqueiam (≈170 teleportes): a rede fica
  acima da sua capacidade e nenhum algoritmo de fases resolve isso.

**Desvios ao plano:**
- Os modos *onda verde* e *escoamento alternado* **não foram implementados**: depois de ver que a camada 2
  já acrescenta pouco, não havia evidência de que mais heurísticas ajudassem, e o prazo é curto. Ficam como
  **2c opcional** no fim, se sobrar tempo.
- `EstadoDoNo` e o barramento de mensagens não existem como tipos: o coordenador lê directamente as leituras
  de faixa de todos os nós e devolve `OrdemDeModo` por nó. A comunicação é, por isso, em memória.
- O Max-Pressure local ganhou uma regra de ceder depressa uma fase **sem nenhum veículo** (5 s em vez de
  20 s). O diagnóstico da semente 13 mostrou que o bloqueio vinha daí (um cruzamento segurava 14 s uma fase
  vazia com 18 carros à espera), e não de spillback, como eu tinha suposto. Com ela, a semente 13 deixou
  de bloquear (de 38 para 5 teleportes) e o local passou de −12 % para −33 % sem incidente.
- Os veículos avariados do incidente ficam fora de todos os KPIs.

**Limitações:** o incidente e a conformidade de 50 % são valores assumidos; as sementes 42, 7 e 13 foram
usadas para afinar o verde mínimo e a histerese do local.

### Fase 2a — Controlo local Max-Pressure (10/10/2026)
Cada um dos 13 semáforos passa a decidir sozinho por Max-Pressure (`controlo/local/max_pressure.py`),
ligado ao SUMO por `simulacao/ponte.py`. Corrida: `... executar --cenario local [--semente N]`.

**Resultado (hora de ponta, espera média em segundos, tempo fixo → local):**

| Semente | Tempo fixo | Local | Variação | Teleportes (fixo → local) |
|---|---|---|---|---|
| 42 | 87,9 | 66,5 | −24 % | 5 → 0 |
| 7 | 135,4 | 74,2 | −45 % | 29 → 1 |
| 13 | 103,2 | 145,5 | **+41 %** | 0 → **38** |
| média | 108,8 | 95,4 | −12 % | |

**Leitura honesta:** o controlo local melhora duas sementes em três, mas na semente 13 a rede entra em
bloqueio (38 teleportes, 4954 s para esvaziar). Sem coordenação, um nó que enche a saída bloqueia o
anterior — exactamente o *spillback* que a camada 2 existe para evitar. A média de −12 % não é
conclusiva com 3 sementes; as comparações finais usarão mais sementes.

**Desvios e achados:**
- Com `verde_minimo` 10 s o cruzamento trocava de fase a cada ~15 s e perdia ~25 % do tempo em amarelos:
  pior do que o tempo fixo (espera 647 s e 101 teleportes numa hora completa). Passou a 20 s com
  histerese 0,2. **Estes valores foram ajustados na semente 42** e validados nas sementes 7 e 13 — o
  resultado da 13 mostra que o ajuste não generaliza por si só.
- A fila de entrada mede-se só com veículos parados e com tecto de 20 veículos: em faixas de 1 km a
  ocupação total escondia filas reais e dava-lhes pressão negativa.
- 3 dos 13 nós (incluindo C5) não trocam de fase: a procura assumida quase não passa por eles.
- A pasta de resultados inclui agora o limite no nome (`_limN`) para um ensaio curto não sobrescrever
  uma corrida completa.

### Fase 1 — Base da simulação (10/10/2026)
Repositório, SUMO 1.28.0 + TraCI, estrutura de módulos, rede do corredor da Av. 24 de Julho
(12 semáforos reais do OSM + C5 forçado, incl. C4 Tanzânia; Eduardo Mondlane paralela como via alternativa),
procura de hora de ponta e simulação de **tempo fixo** com KPIs repetíveis.

- Rede: `uv run python -m gestao_trafego.simulacao.construir_rede` → `dados/cenarios/corredor_24_de_julho.net.xml`
- Procura: `dados/cenarios/procura_hora_de_ponta.json` (10 fluxos, 4 tipos de veículo, **valores assumidos**)
- Corrida: `uv run python -m gestao_trafego.simulacao.executar --cenario fixo [--escala X] [--semente N]`
- Testes: `uv run pytest` (5 testes; os 2 de repetibilidade correm o SUMO, ~20 s)

**Linha de base (tempo fixo, hora de ponta, semente 42, 13 semáforos):** 2000 veículos concluídos em 4074 s
simulados; espera média **87,9 s** (desvio 78,2 s); perda de tempo média 126 s; duração média de viagem
328 s; fila média 45 veículos parados (máxima 124); velocidade média 8,0 m/s; **5 teleportes**, 0 colisões.

**Desvios ao plano:** o Overpass falhou (406/500/504), pelo que o OSM é descarregado por quadrantes
da API principal. Com o dobro dos fluxos iniciais (3950 veh/h) o tempo fixo entrava em bloqueio total
(espera média 574 s, 180 teleportes) — fluxos reduzidos a metade; `--escala 2` fica como cenário de
stress. C5 (Eduardo Mondlane × Albert Luthuli) tem semáforo na realidade mas não no OSM: é forçado em `SEMAFOROS_FORCADOS` (`construir_rede.py`), que falha alto se o id do cruzamento mudar. Com ele a linha de base passou de 0 para 5 teleportes (programa de tempo fixo gerado por defeito para esse nó, não medido).

**Limitações:** procura e tempos semafóricos assumidos (sem planilha de campo); os programas de tempo
fixo são os que o `netconvert` gera, não os medidos em Maputo.

---

## 2. Arquitectura

Dois fluxos paralelos que se encontram no mesmo formato de dado: **contagem por via**.

```
Fluxo 1 — Percepção            vídeo → OpenCV → YOLO → tracking → linha de contagem → ContagemPorVia
Fluxo 2 — Simulação e decisão  SUMO ⇄ TraCI ⇄ Controlo (camada 1 + camada 2) → fases dos semáforos
```

O SUMO não gera imagem de câmara. Na simulação, os detectores do SUMO fazem o papel das câmaras; no
vídeo real, o YOLO produz o mesmo tipo de dado. O algoritmo só vê `ContagemPorVia`.

### 2.1 Controlo em duas camadas (decisão de 10/10/2026)

- **Camada 1 — local (Max-Pressure):** um controlador por cruzamento. Escolhe a fase com maior
  pressão (carros a entrar − carros nas vias de saída). Respeita verde mínimo, amarelo e vermelho
  máximo (peões). Sem ordem do coordenador, decide sozinho — se a coordenação falhar, o cruzamento
  continua a funcionar.
- **Camada 2 — coordenador:** *implementado:* anti-bloqueio (*gating* com propagação a montante) e vias
  alternativas (ver Histórico, Fase 2b). *Não implementado (2c opcional):* onda verde e escoamento
  alternado. Desenho original, que atribui **modos** com duração:
  - *gating*: reduz o verde da entrada a montante, para parar de alimentar a zona saturada;
  - *onda verde*: verde longo no corredor, com desfasamento entre nós;
  - *escoamento alternado*: quando a fila numa travessa passa o limite, dá-lhe verde (~7 s) e
    devolve ao corredor (~15 s) — **parâmetros a calibrar na simulação**;
  - *vias alternativas*: re-encaminhamento de parte dos veículos (`rerouteTraveltime`).
- **Comunicação:** cada nó publica `EstadoDoNo` (filas, espaço livre nas saídas, espera máxima, fase
  actual); o coordenador devolve `OrdemDeModo`. No protótipo é um barramento em memória; em produção
  seria MQTT/rede dedicada (fica na monografia como trabalho de implantação).
- **Nota:** "todos vermelhos no corredor" piora a saturação — dar verde a uma via cheia à frente não
  escoa ninguém. O desenho é travar a entrada e dar verde onde há espaço.

### 2.2 Onde está a IA (para a defesa)

| Parte | Técnica | IA treinada? |
|---|---|---|
| Percepção | YOLO (CNN) | Sim |
| Previsão de saturação | LSTM | Sim |
| Controlo local e coordenação | Heurística adaptativa (Max-Pressure + máquina de estados) | Não |
| Assistente do dashboard | LLM, **só leitura**, nunca controla semáforos | Sim (opcional) |

A monografia (1.6.2) admite "Reinforcement Learning **ou heurísticas adaptativas**". RL multi-agente
(MA-PPO/CoLight via `sumo-rl`) fica como trabalho futuro: treino longo em CPU e menos explicável.

---

## 3. Estrutura de pastas

```
Monografia/
  backend/                          Python 3.12, gerido por uv
    gestao_trafego/
      comum/                        tipos e contratos partilhados
      visao/                        OpenCV + YOLO + contagem
      simulacao/                    SUMO: mapa, rotas, ponte TraCI
      controlo/
        local/                      camada 1: Max-Pressure
        coordenador/                camada 2: modos de corredor
      previsao/                     LSTM
      assistente/                   LLM só de leitura (opcional)
      dados/                        PostgreSQL, métricas
      api/                          FastAPI + WebSocket
    tests/
    scripts/
  frontend/                         React + Vite (dashboard)
  dados/                            vídeos, mapas, cenários, resultados (pesados: fora do Git)
  docs/
    plano_implementacao.md          este documento
    monografia/                     .docx original e conversão em Markdown
```

Regras: a lógica de `controlo/`, `previsao/` e `visao/` é pura (sem HTTP, sem importar `traci`
directamente) — assim serve a demo e os testes. Só `simulacao/` fala com o SUMO e só `api/` fala HTTP.
Código, identificadores e mensagens em português.

---

## 4. Backlog por fases

### Fase 2 — Controlo (dias 3–5) — feita, ver Histórico
- [x] Tipos partilhados, ponte TraCI, Max-Pressure local (camada 1)
- [x] Coordenador anti-bloqueio com propagação e válvula de alívio (camada 2)
- [x] Vias alternativas via `rerouteTraveltime` (conformidade de 50 %)
- [x] Cenário de incidente (via cortada) e comparação de 5 configurações em 8 sementes
- [x] Testes unitários das regras (controlador, coordenador, métricas)
- [ ] *2c opcional:* onda verde e escoamento alternado (só se sobrar tempo)
- [ ] Cenário de hora normal (`--escala 0.5`) incluído na tabela final

### Fase 3 — Visão (dias 6–8) — feita, ver Histórico (falta medir a precisão)
- [x] Vídeo público (Pexels, autoestrada); fonte registada
- [x] YOLO nano em CPU por tipo (carro, mota, autocarro, camião) e velocidade medida
- [x] Seguimento (ByteTrack) e linha virtual de contagem por via; estimativa de fila
- [x] Vídeo anotado com caixas, contadores e janela ao vivo
- [x] Saída em `ContagemPorVia` por janelas de tempo
- [x] Testes da lógica (contagem, fila, janelas, extrapolação) sem o YOLO
- [ ] **Precisão:** contagem manual de um trecho contra a automática (depende de uma pessoa)
- [ ] Ligar a visão ao controlo na demo (a `ContagemPorVia` da câmara ao lado da da simulação)

### Fase 4 — Previsão, dados e API (dias 9–11)
- [x] PostgreSQL decidido e a funcionar (embebido, sem instalação)
- [x] Persistência: execuções, séries, contagens da visão e previsões
- [x] LSTM treinado e avaliado contra a linha de base de persistência
- [ ] `SessaoDeSimulacao` (refactor) e simulação ao vivo
- [ ] FastAPI + WebSocket
- [ ] Dashboard React
- [ ] Testes da API

### Fase 5 — Assistente, resultados e ensaio (dias 12–14)
- [ ] Resultados e gráficos para a monografia (média, desvio-padrão, antes/depois — secção 3.10)
- [ ] Assistente LLM (opcional, **primeira peça a cortar** se o prazo apertar): funções fixas
      (`fluxo_por_via`, `horas_de_ponta`, `tipos_de_veiculo`, `vias_mais_movimentadas`,
      `comparar_cenarios`), relatório automático, voz via Web Speech API; respostas pré-gravadas
      como modo de segurança se não houver rede na defesa
- [ ] Ensaio completo da demonstração; guião de defesa

---

## 5. Decisões e assunções

| Data | Decisão |
|---|---|
| 10/10/2026 | Rede **ligada** (opção A): corredor que inclua C4 (24 de Julho/Tanzânia) e C5 (Eduardo Mondlane/Albert Luthuli); os 5 cruzamentos da Tabela 1 são a amostra do levantamento de campo |
| 10/10/2026 | Controlo em duas camadas (secção 2.1) |
| 10/10/2026 | Sem planilha de campo por agora: procura e tempos semafóricos assumidos, em ficheiro de configuração, substituíveis |
| 10/10/2026 | Vídeo: público (não há gravação própria) |
| 10/10/2026 | LLM só no dashboard, só leitura; nunca decide sobre semáforos. Texto e voz em tempo real: **Gemini**. Síntese de voz (texto -> áudio), por ordem de preferência: Google TTS, ElevenLabs. Todas as chaves em `backend/.env` (fora do Git); variáveis documentadas em `backend/.env.example` |

**Assunções por validar:** C4 e C5 ligam-se pelo corredor (confirmado no mapa: C4 a oeste, C5 junto à Guerra Popular);
que o YOLO nano em CPU atinge taxa suficiente para a demo.

---

## 6. Riscos e limitações (a dizer com honestidade na defesa)

- **Índice de acidentes:** o SUMO não produz acidentes reais. Só colisões simuladas, travagens bruscas e
  situações de risco. É um *indicador de risco simulado*, não estatística real.
- **Visão em CPU:** 1,7 a 6,9 fotogramas/s consoante a resolução; não serve câmara em tempo real neste
  computador e a contagem ao vivo subconta (ver Histórico, Fase 3). A demo mostra o vídeo anotado já processado.
- **Vídeo ≠ simulação:** a ligação é por formato de dado, validada por módulos — não há câmara real a
  alimentar o SUMO.
- **Calibração:** sem a planilha de Agosto, os cenários não estão calibrados com dados reais. A monografia
  (3.3.1, 3.4) afirma que estão — trazer a planilha antes da defesa.
- **Rede na defesa:** o assistente LLM precisa de internet; manter modo de segurança.
- **Prazo:** 2 semanas. Cortes por ordem: assistente LLM → vias alternativas → LSTM. O núcleo
  (simulação, controlo em duas camadas, visão, dashboard) não se corta.

---

## 7. Pendências do utilizador

- [ ] ~~Planilha Excel da observação directa~~ — não disponível; trabalha-se sem ela (valores assumidos). Trazê-la antes da defesa se possível
- [x] Modelo do assistente: Gemini; chave e modelos em `backend/.env` (fora do Git)
- [ ] Contar à mão os carros que cruzam a linha nos primeiros 30 s do vídeo anotado
      (`dados/resultados/visao_autoestrada_completo/anotado.mp4`; o sistema contou 26) e dizer o número
- [ ] Corrigir na monografia: nome do C3 (3.3.1 vs Tabela 1), secções por numerar/ordenar, notas internas
      e referências duplicadas, e descrever em 3.7.5 as duas camadas de controlo
