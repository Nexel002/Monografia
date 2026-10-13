"""LSTM que prevê os veículos parados em vários horizontes (PyTorch, em CPU)."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn

from gestao_trafego.previsao.dataset import COLUNA_ALVO, Janelas, Normalizacao


class RedeLSTM(nn.Module):
    def __init__(self, n_variaveis: int, n_horizontes: int, escondido: int = 32):
        super().__init__()
        self.lstm = nn.LSTM(n_variaveis, escondido, batch_first=True)
        self.saida = nn.Linear(escondido, n_horizontes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        saidas, _ = self.lstm(x)
        return self.saida(saidas[:, -1, :])  # só o estado do último passo da janela


@dataclass
class ModeloTreinado:
    rede: RedeLSTM
    normalizacao: Normalizacao
    horizontes_passos: tuple[int, ...]
    recuo: int

    def prever(self, entradas: np.ndarray) -> np.ndarray:
        """Previsões em veículos parados (já fora do espaço normalizado), uma coluna por horizonte."""
        self.rede.eval()
        with torch.no_grad():
            normalizadas = torch.from_numpy(self.normalizacao.aplicar(entradas))
            previsto = self.rede(normalizadas).numpy()
        media, desvio = self.normalizacao.media[COLUNA_ALVO], self.normalizacao.desvio[COLUNA_ALVO]
        return np.maximum(previsto * desvio + media, 0.0)  # uma fila não pode ser negativa

    def guardar(self, caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "estado": self.rede.state_dict(),
                "media": self.normalizacao.media,
                "desvio": self.normalizacao.desvio,
                "horizontes_passos": self.horizontes_passos,
                "recuo": self.recuo,
                "escondido": self.rede.lstm.hidden_size,
            },
            caminho,
        )

    @staticmethod
    def carregar(caminho: Path) -> "ModeloTreinado":
        dados = torch.load(caminho, weights_only=False)
        rede = RedeLSTM(len(dados["media"]), len(dados["horizontes_passos"]), dados["escondido"])
        rede.load_state_dict(dados["estado"])
        return ModeloTreinado(rede, Normalizacao(dados["media"], dados["desvio"]), tuple(dados["horizontes_passos"]), dados["recuo"])


def treinar(
    janelas: Janelas,
    horizontes_passos: tuple[int, ...],
    recuo: int,
    epocas: int = 30,
    escondido: int = 32,
    semente: int = 0,
    taxa: float = 0.01,
    tamanho_do_lote: int = 128,
) -> tuple[ModeloTreinado, list[float]]:
    """Devolve o modelo e a perda (erro quadrático médio, normalizado) de cada época."""
    torch.manual_seed(semente)
    normalizacao = Normalizacao.ajustar(janelas.entradas)
    x = torch.from_numpy(normalizacao.aplicar(janelas.entradas))
    media, desvio = normalizacao.media[COLUNA_ALVO], normalizacao.desvio[COLUNA_ALVO]
    y = torch.from_numpy(((janelas.alvos - media) / desvio).astype(np.float32))

    rede = RedeLSTM(x.shape[-1], y.shape[-1], escondido)
    optimizador = torch.optim.Adam(rede.parameters(), lr=taxa)
    perdas = []
    for _ in range(epocas):
        rede.train()
        ordem = torch.randperm(len(x))
        total = 0.0
        for inicio in range(0, len(x), tamanho_do_lote):
            lote = ordem[inicio : inicio + tamanho_do_lote]
            optimizador.zero_grad()
            perda = nn.functional.mse_loss(rede(x[lote]), y[lote])
            perda.backward()
            optimizador.step()
            total += perda.item() * len(lote)
        perdas.append(total / len(x))
    return ModeloTreinado(rede, normalizacao, horizontes_passos, recuo), perdas
