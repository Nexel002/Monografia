# Plano de Implementação — Protótipo da Monografia

Sistema integrado com IA para apoio à gestão de tráfego rodoviário na Cidade e Província de Maputo.
Este é o **único** documento de planeamento do protótipo. A monografia vive em `docs/monografia/`.

**Prazo:** 2 semanas a contar de 10/10/2026. **Nível:** licenciatura. **Objectivo:** protótipo funcional
e demonstrável na defesa, que prove que a ideia é viável — não um sistema de produção.

---

## 1. Fase em curso

**Fase 1 — Base da simulação (dias 1–2)**

- [x] Repositório criado e ligado à conta Nexel (SSH `github-nexel`)
- [x] Monografia convertida para Markdown (`docs/monografia/monografia.md`)
- [x] SUMO 1.28.0 + TraCI + sumolib instalados (`backend/.venv`, gerido por `uv`, Python 3.12)
- [x] Estrutura de pastas criada (secção 3)
- [x] Rede importada: corredor da **Av. 24 de Julho** (12 semáforos reais do OSM, incl. C4 Tanzânia) + Av. Eduardo Mondlane paralela como via alternativa. Reproduzível: `uv run python -m gestao_trafego.simulacao.construir_rede` (rede em `dados/cenarios/corredor_24_de_julho.net.xml`)
- [ ] Gerar procura de hora de ponta (`routes.rou.xml`) — valores assumidos, em ficheiro de configuração
- [ ] Correr a rede com semáforos de **tempo fixo** (cenário de referência) e gravar métricas
- [ ] Teste: a simulação arranca, termina e produz KPIs repetíveis (mesma semente → mesmo resultado)

**Como verificar:** `cd backend && uv run python -m gestao_trafego.simulacao.executar --cenario fixo`
deve correr sem erros e escrever as métricas em `dados/resultados/`. *(Comando previsto; confirmar quando existir.)*

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
| 10/10/2026 | LLM só no dashboard, só leitura; nunca decide sobre semáforos. Fornecedor: **Gemini** (texto e voz em tempo real); variáveis em `backend/.env`, modelo em `.env.example` |

**Assunções por validar:** que C4 e C5 se ligam por um corredor de cruzamentos reais (verificar no mapa);
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
