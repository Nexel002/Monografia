from pathlib import Path

from gestao_trafego.simulacao.metricas import Amostra, Viagem, ler_viagens, resumir


def test_resumir_calcula_medias_e_maximo_de_fila():
    viagens = [Viagem(10, 12, 100), Viagem(30, 35, 140)]
    amostras = [Amostra(10, 5, 2, 8.0), Amostra(20, 9, 7, 4.0)]

    resumo = resumir(viagens, amostras, nao_concluidos=3, teleportes=1, colisoes=0, tempo_simulado_s=20)

    assert resumo["espera_media_s"] == 20
    assert resumo["espera_desvio_padrao_s"] == 10
    assert resumo["duracao_viagem_media_s"] == 120
    assert resumo["fila_media_veiculos"] == 4.5
    assert resumo["fila_maxima_veiculos"] == 7
    assert resumo["velocidade_media_ms"] == 6.0
    assert resumo["veiculos_nao_concluidos"] == 3


def test_resumir_sem_dados_nao_rebenta():
    resumo = resumir([], [], nao_concluidos=0, teleportes=0, colisoes=0, tempo_simulado_s=0)

    assert resumo["espera_media_s"] == 0.0
    assert resumo["fila_maxima_veiculos"] == 0


def test_ler_viagens_do_tripinfo(tmp_path: Path):
    ficheiro = tmp_path / "tripinfo.xml"
    ficheiro.write_text(
        '<tripinfos><tripinfo id="a" waitingTime="5.5" timeLoss="9" duration="60"/></tripinfos>',
        encoding="utf-8",
    )

    assert ler_viagens(ficheiro) == [Viagem(5.5, 9.0, 60.0)]
