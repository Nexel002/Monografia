import pytest

from gestao_trafego.comum.tipos import ContagemPorVia
from gestao_trafego.visao.contagem import Caixa, Deteccao, Passagem
from gestao_trafego.visao.fila import EstimadorDeFila, agregar_por_janela

ZONA = (0.0, 0.0, 200.0, 100.0)


def carro(id_, x=50.0, y_base=80.0) -> Deteccao:
    return Deteccao(id_, Caixa(x - 20, y_base - 40, x + 20, y_base), "carro")


def test_veiculo_imovel_na_zona_conta_como_parado():
    e = EstimadorDeFila(ZONA)
    e.actualizar(0, [carro(1)])

    assert e.actualizar(1, [carro(1)]) == 1


def test_veiculo_em_movimento_nao_conta():
    e = EstimadorDeFila(ZONA)
    e.actualizar(0, [carro(1, y_base=60)])

    assert e.actualizar(1, [carro(1, y_base=70)]) == 0


def test_primeira_vez_que_se_ve_o_veiculo_nao_conta_como_parado():
    assert EstimadorDeFila(ZONA).actualizar(0, [carro(1)]) == 0


def test_veiculo_parado_fora_da_zona_nao_conta():
    e = EstimadorDeFila(ZONA)
    e.actualizar(0, [carro(1, y_base=300)])

    assert e.actualizar(1, [carro(1, y_base=300)]) == 0


def test_velocidade_normaliza_pelo_intervalo_entre_analises():
    e = EstimadorDeFila(ZONA)
    e.actualizar(0, [carro(1, y_base=60)])

    # 4 px em 10 fotogramas = 0,4 px/fotograma = 0,01 alturas/fotograma > 0,004: está a andar.
    assert e.actualizar(10, [carro(1, y_base=64)]) == 0
    # 1 px em 10 fotogramas = 0,0025 alturas/fotograma: parado.
    assert e.actualizar(20, [carro(1, y_base=65)]) == 1


def passagem(fotograma, tipo="carro") -> Passagem:
    return Passagem(1, tipo, "volta", fotograma)


def test_agrega_passagens_e_fila_por_janela():
    passagens = [passagem(30), passagem(60, "camiao"), passagem(400)]  # fps 30: 1 s, 2 s, 13,3 s
    filas = [(0, 2), (150, 4), (400, 6)]

    janelas = agregar_por_janela("via_a", passagens, filas, fps=30, duracao_s=20, janela_s=10)

    assert [j.por_tipo for j in janelas] == [{"carro": 1, "camiao": 1}, {"carro": 1}]
    assert [j.fila_media_veiculos for j in janelas] == [3.0, 6.0]  # (2+4)/2 e 6
    assert [(j.inicio_s, j.fim_s) for j in janelas] == [(0, 10), (10, 20)]


def test_ultima_janela_pode_ser_mais_curta_e_o_fluxo_usa_a_duracao_real():
    janelas = agregar_por_janela("v", [passagem(30 * 11)], [], fps=30, duracao_s=15, janela_s=10)

    assert janelas[-1].fim_s == 15
    assert janelas[-1].fluxo_veiculos_por_hora == 1 * 3600 / 5


def test_contagem_sem_dados_e_zero():
    c = ContagemPorVia("v", 0, 10, {}, 0.0)

    assert c.total == 0 and c.fluxo_veiculos_por_hora == 0


def test_janela_invalida_falha_alto():
    with pytest.raises(ValueError):
        agregar_por_janela("v", [], [], fps=30, duracao_s=10, janela_s=0)
