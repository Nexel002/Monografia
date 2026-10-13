"""Onde o treino guarda o modelo e as métricas. Num módulo à parte e sem PyTorch: quem só quer ler as métricas
(a API, o assistente) não deve pagar os segundos que custa importar o PyTorch."""

from gestao_trafego.comum.configuracao import RAIZ

CAMINHO_DO_MODELO = RAIZ / "dados" / "modelos" / "lstm.pt"
CAMINHO_DAS_METRICAS = RAIZ / "dados" / "resultados" / "previsao_metricas.json"
