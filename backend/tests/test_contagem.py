import pytest

from gestao_trafego.visao.contagem import SENTIDO_IDA, SENTIDO_VOLTA, Caixa, ContadorDeLinha, Deteccao

# Linha horizontal em y=100, de x=0 a x=200 (as imagens têm o y a crescer para baixo).
A, B = (0.0, 100.0), (200.0, 100.0)


def veiculo(id_, y_base, x=100.0, tipo="carro", altura=40.0) -> Deteccao:
    return Deteccao(id_, Caixa(x - 20, y_base - altura, x + 20, y_base), tipo)


def percorrer(contador: ContadorDeLinha, id_, ys, **kwargs):
    for i, y in enumerate(ys):
        contador.actualizar(i, [veiculo(id_, y, **kwargs)])


def test_caixa_base_e_centro():
    caixa = Caixa(10, 20, 30, 60)

    assert caixa.base == (20, 60)
    assert caixa.centro == (20, 40)


def test_veiculo_que_sobe_atravessa_a_linha_no_sentido_ida():
    c = ContadorDeLinha(A, B)

    percorrer(c, 1, [140, 120, 95, 70])

    assert c.por_sentido() == {SENTIDO_IDA: 1, SENTIDO_VOLTA: 0}
    assert c.total() == 1


def test_veiculo_que_desce_conta_no_sentido_volta():
    c = ContadorDeLinha(A, B)

    percorrer(c, 1, [60, 90, 110, 130])

    assert c.por_sentido() == {SENTIDO_IDA: 0, SENTIDO_VOLTA: 1}


def test_conta_os_dois_sentidos_na_mesma_linha():
    c = ContadorDeLinha(A, B)
    for i, (ya, yb) in enumerate([(140, 60), (120, 80), (95, 105), (70, 130)]):
        c.actualizar(i, [veiculo(1, ya, x=60), veiculo(2, yb, x=140)])

    assert c.por_sentido() == {SENTIDO_IDA: 1, SENTIDO_VOLTA: 1}
    assert c.total() == 2


def test_nao_conta_duas_vezes_o_mesmo_veiculo_que_oscila_sobre_a_linha():
    c = ContadorDeLinha(A, B)

    percorrer(c, 1, [90, 110, 90, 110, 90])

    assert c.total() == 1


def test_veiculo_que_aparece_ja_depois_da_linha_nao_conta():
    c = ContadorDeLinha(A, B)

    percorrer(c, 1, [60, 50, 40])

    assert c.total() == 0


def test_movimento_fora_do_segmento_nao_conta():
    c = ContadorDeLinha(A, B)

    percorrer(c, 1, [140, 60], x=500.0)  # cruza a recta, mas muito para lá da ponta do segmento

    assert c.total() == 0


def test_a_base_conta_antes_do_centro_num_veiculo_alto():
    # Veículo de 100 px de altura a subir: a base chega à linha primeiro que o centro.
    base = ContadorDeLinha(A, B, ponto="base")
    centro = ContadorDeLinha(A, B, ponto="centro")
    for i, y_base in enumerate([180, 150, 120, 98]):
        d = [veiculo(1, y_base, altura=100.0)]
        base.actualizar(i, d)
        centro.actualizar(i, d)

    assert base.total() == 1
    assert centro.total() == 0


def test_conta_por_tipo_e_marca_os_ids_contados():
    c = ContadorDeLinha(A, B)
    percorrer(c, 1, [140, 60], tipo="camiao")
    percorrer(c, 2, [140, 60], tipo="mota")

    assert c.por_tipo() == {"camiao": 1, "mota": 1}
    assert c.foi_contado(1) and c.foi_contado(2) and not c.foi_contado(3)


def test_actualizar_devolve_so_as_passagens_novas():
    c = ContadorDeLinha(A, B)
    c.actualizar(0, [veiculo(1, 140)])

    novas = c.actualizar(1, [veiculo(1, 60)])

    assert [p.id_veiculo for p in novas] == [1]
    assert c.actualizar(2, [veiculo(1, 40)]) == []


def test_linha_invalida_falha_alto():
    with pytest.raises(ValueError):
        ContadorDeLinha(A, A)
    with pytest.raises(ValueError):
        ContadorDeLinha(A, B, ponto="topo")
