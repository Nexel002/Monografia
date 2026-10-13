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

O dashboard tem quatro ecrãs: **Simulação ao vivo** (dois cenários lado a lado), **Resultados**,
**Previsão** e **Visão computacional**. Testes: `uv run pytest` (backend) e `npm test` (frontend).
