from gestao_trafego.visao.contagem import Caixa, Deteccao
from gestao_trafego.visao.extrapolar import ExtrapoladorDeCaixas


def veiculo(id_, x, y=100.0) -> Deteccao:
    return Deteccao(id_, Caixa(x, y, x + 40, y + 40), "carro")


def test_sem_historico_as_caixas_ficam_onde_o_detector_as_viu():
    e = ExtrapoladorDeCaixas()
    e.actualizar(10, [veiculo(1, 50)])

    assert e.prever(14)[0].caixa == Caixa(50, 100, 90, 140)


def test_depois_de_duas_analises_a_caixa_avanca_a_velocidade_medida():
    e = ExtrapoladorDeCaixas()
    e.actualizar(0, [veiculo(1, 0)])
    e.actualizar(10, [veiculo(1, 20)])  # 2 px por fotograma

    assert e.prever(15)[0].caixa.x1 == 30  # 20 + 5 fotogramas * 2 px


def test_a_extrapolacao_tem_limite():
    e = ExtrapoladorDeCaixas(maximo_de_fotogramas=5)
    e.actualizar(0, [veiculo(1, 0)])
    e.actualizar(10, [veiculo(1, 20)])

    assert e.prever(500)[0].caixa.x1 == 30  # só avança 5 fotogramas


def test_so_se_mostram_os_veiculos_da_ultima_analise():
    e = ExtrapoladorDeCaixas()
    e.actualizar(0, [veiculo(1, 0), veiculo(2, 100)])
    e.actualizar(5, [veiculo(2, 110)])

    assert [d.id_veiculo for d in e.prever(6)] == [2]


def test_nao_recua_se_o_indice_pedido_for_anterior():
    e = ExtrapoladorDeCaixas()
    e.actualizar(0, [veiculo(1, 0)])
    e.actualizar(10, [veiculo(1, 20)])

    assert e.prever(3)[0].caixa.x1 == 20
