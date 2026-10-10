# Plano de Implementação — Protótipo da Monografia

Sistema integrado com IA para apoio à gestão de tráfego rodoviário na Cidade e Província de Maputo.
Este é o **único** documento de planeamento do protótipo. A monografia vive em `docs/monografia/`.

**Prazo:** 2 semanas a contar de 10/10/2026. **Nível:** licenciatura. **Objectivo:** protótipo funcional
e demonstrável na defesa, que prove que a ideia é viável — não um sistema de produção.

---

## 1. Fase em curso

**Fase 2 — Controlo em duas camadas (dias 3–5)**

- [ ] `EstadoDoNo`, `OrdemDeModo`, `ContagemPorVia` em `comum/`
- [ ] Ponte TraCI por nó: ler filas/espaço livre nas saídas e aplicar fases (`simulacao/`)
- [ ] Camada 1: Max-Pressure por cruzamento, com verde mínimo / amarelo / vermelho máximo
- [ ] Camada 2: coordenador com modos *gating*, *onda verde*, *escoamento alternado*
- [ ] Vias alternativas via `rerouteTraveltime`
- [ ] Cenário `inteligente` em `executar.py`; comparação com `fixo` (mesma semente, mesmos veículos)
- [ ] Cenários: hora de ponta (`--escala 1`), normal (`0.5`), incidente (via cortada)
- [ ] Testes unitários das regras (pressão, limiares, duração dos modos, regresso ao normal)

**Como verificar:** `cd backend && uv run python -m gestao_trafego.simulacao.executar --cenario inteligente`
e comparar `dados/resultados/*/resumo.json` com o do cenário `fixo`.

---

## 1.1 Histórico de entregas

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
- **Camada 2 — coordenador de corredor:** lê o estado de todos os nós e atribui **modos** com duração:
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

### Fase 2 — Controlo (dias 3–5)
- [ ] `EstadoDoNo`, `OrdemDeModo`, `ContagemPorVia` em `comum/`
- [ ] Camada 1: Max-Pressure por cruzamento, com verde mínimo / amarelo / vermelho máximo
- [ ] Camada 2: coordenador com modos *gating*, *onda verde*, *escoamento alternado*
- [ ] Vias alternativas via `rerouteTraveltime`
- [ ] Comparação **fixo vs local vs local+coordenador** nos mesmos cenários (hora de ponta, normal, incidente)
- [ ] Testes unitários das regras (pressão, limiares, duração dos modos, regresso ao normal)

### Fase 3 — Visão (dias 6–8)
- [ ] Escolher vídeo público de tráfego (cruzamento, câmara fixa)
- [ ] YOLO nano em CPU: detecção por tipo (carro, camião, mota, autocarro)
- [ ] Tracking + linha virtual de contagem; estimativa de fila
- [ ] Vídeo anotado com contadores; medir precisão da contagem contra contagem manual
- [ ] Saída no formato `ContagemPorVia`

### Fase 4 — Previsão, dados e API (dias 9–11)
- [ ] Séries de contagens geradas pelo SUMO → LSTM pequeno (CPU) → previsão de filas
- [ ] PostgreSQL: execuções, métricas por passo, decisões do coordenador
- [ ] FastAPI + WebSocket: estado ao vivo, comparação fixo vs inteligente
- [ ] Dashboard React: mapa/estado dos semáforos, filas, previsão vs real, KPIs, vídeo anotado

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
- [ ] Corrigir na monografia: nome do C3 (3.3.1 vs Tabela 1), secções por numerar/ordenar, notas internas
      e referências duplicadas, e descrever em 3.7.5 as duas camadas de controlo
