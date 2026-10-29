# Monografia

Sistema integrado com IA para apoio à gestão de tráfego rodoviário na Cidade e Província de Maputo.

Protótipo: semáforos como nós de uma rede, com visão computacional (OpenCV + YOLO), simulação no SUMO,
controlo em duas camadas (Max-Pressure local + coordenador de corredor), previsão com LSTM,
PostgreSQL, API FastAPI e dashboard em React.

- Plano, decisões e resultados: [`docs/plano_implementacao.md`](docs/plano_implementacao.md)
- Monografia: [`docs/monografia/`](docs/monografia/)

## Arranque

Precisa de Python 3.12 (gerido pelo `uv`) e Node.js. A primeira instalação descarrega o PyTorch (grande).

```
# 1. Backend (terminal 1)
cd backend
uv sync
uv run python -m gestao_trafego.dados.importar      # importa os resultados guardados para o PostgreSQL embebido
uv run uvicorn gestao_trafego.api.app:criar_app --factory --port 8000

# 2. Dashboard (terminal 2)
cd frontend
npm install
npm run dev                                          # http://localhost:5174
```

**Vídeos da visão computacional:** põe o vídeo (qualquer formato) em `dados/videos/` e converte-o para WebM, que é
o único formato que o backend lê (fica em `dados/videos_webm/`):

```
cd backend
uv run python -m gestao_trafego.visao.video --converter-tudo
```

**Se o backend falhar com «Timeout starting server»:** o PostgreSQL embebido ficou mal fechado (PC desligado à força) e a
recuperação demora mais do que os 10 s que o `pgserver` espera. Ver «Base de dados embebida» em `docs/plano_implementacao.md`, secção 6.

O dashboard tem quatro ecrãs: **Simulação ao vivo** (dois cenários lado a lado), **Resultados**,
**Previsão** e **Visão computacional**. Testes: `uv run pytest` (backend) e `npm test` (frontend).
