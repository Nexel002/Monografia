from gestao_trafego.comum.tipos import FaseVerde, LeituraDeFaixa, Movimento, TopologiaDoNo
from gestao_trafego.controlo.local.max_pressure import ControladorLocal, ParametrosLocais, estado_de_amarelo

# Cruzamento mínimo: a fase 0 serve a1 -> b1 (sinal 0) e a fase 1 serve a2 -> b2 (sinal 1).
TOPOLOGIA = TopologiaDoNo(
    "no",
    (
        FaseVerde(0, "Gr", (Movimento("a1", "b1"),)),
        FaseVerde(1, "rG", (Movimento("a2", "b2"),)),
    ),
)
PARAMETROS = ParametrosLocais(verde_minimo_s=10, verde_maximo_s=60, amarelo_s=4, vermelho_maximo_s=120, histerese=0.1)


def faixa(parados: int = 0, veiculos: int | None = None, capacidade: float = 20) -> LeituraDeFaixa:
    return LeituraDeFaixa(veiculos=parados if veiculos is None else veiculos, parados=parados, capacidade=capacidade)


def leitura(a1=0, a2=0, b1=0, b2=0) -> dict[str, LeituraDeFaixa]:
    return {"a1": faixa(a1), "a2": faixa(a2), "b1": faixa(b1), "b2": faixa(b2)}


def avancar(controlador: ControladorLocal, de_s: int, ate_s: int, lei) -> str:
    estado = controlador.estado
    for t in range(de_s, ate_s + 1):
        estado = controlador.passo(t, lei)
    return estado


def test_estado_de_amarelo_fecha_o_que_fecha_e_mantem_o_que_continua():
    assert estado_de_amarelo("GGgr", "rrGG") == "yyGr"
    assert estado_de_amarelo("Gr", "rG") == "yr"
    assert estado_de_amarelo("GG", "Gr") == "Gy"
    assert estado_de_amarelo("rr", "GG") == "rr"


def test_nao_troca_antes_do_verde_minimo_mesmo_com_pressao_maior_na_outra_fase():
    c = ControladorLocal(TOPOLOGIA, PARAMETROS)

    estado = avancar(c, 1, 9, leitura(a1=0, a2=20))

    assert estado == "Gr"


def test_troca_para_a_fase_de_maior_pressao_passando_por_amarelo():
    c = ControladorLocal(TOPOLOGIA, PARAMETROS)
    lei = leitura(a1=0, a2=20)

    assert avancar(c, 1, 10, lei) == "yr"  # verde mínimo cumprido: começa o amarelo
    assert avancar(c, 11, 13, lei) == "yr"  # ainda amarelo
    assert avancar(c, 14, 14, lei) == "rG"  # amarelo de 4 s acabou
    assert c.fase == 1


def test_histerese_evita_trocar_por_diferenca_pequena():
    c = ControladorLocal(TOPOLOGIA, PARAMETROS)
    # a1 = 10/20 = 0,5 ; a2 = 11/20 = 0,55 -> diferença 0,05 < histerese 0,1
    estado = avancar(c, 1, 30, leitura(a1=10, a2=11))

    assert estado == "Gr"


def test_saida_cheia_tira_a_pressao_a_uma_fase():
    c = ControladorLocal(TOPOLOGIA, PARAMETROS)
    # a1 tem fila máxima mas b1 está cheia: pressão 1 - 1 = 0. a2 tem fila média e saída livre.
    lei = {"a1": faixa(20), "b1": faixa(20), "a2": faixa(10), "b2": faixa(0)}

    assert c.pressao(0, lei) == 0
    assert c.pressao(1, lei) == 0.5
    assert avancar(c, 1, 10, lei) == "yr"


def test_fase_sem_procura_nao_ganha_verde_forcado_pelo_vermelho_maximo():
    c = ControladorLocal(TOPOLOGIA, PARAMETROS)

    estado = avancar(c, 1, 300, leitura(a1=5, a2=0))

    assert estado == "Gr"


def test_vermelho_maximo_obriga_a_servir_fase_esquecida_com_procura():
    c = ControladorLocal(TOPOLOGIA, ParametrosLocais(10, 1000, 4, 120, 0.1))
    # a1 tem sempre mais fila e ganharia para sempre; a2 tem 1 carro à espera.
    lei = leitura(a1=20, a2=1)
    estado = avancar(c, 1, 119, lei)
    assert estado == "Gr"

    assert avancar(c, 120, 121, lei) == "yr"


def test_verde_maximo_passa_a_vez_a_outra_fase_com_procura():
    c = ControladorLocal(TOPOLOGIA, ParametrosLocais(10, 30, 4, 1000, 0.1))
    # a1 domina (pressão 1,0 contra 0,05), mas ao fim do verde máximo a2 tem de passar.
    lei = leitura(a1=20, a2=1)

    assert avancar(c, 1, 29, lei) == "Gr"
    assert avancar(c, 30, 30, lei) == "yr"


def test_sem_fases_verdes_falha_alto():
    import pytest

    with pytest.raises(ValueError):
        ControladorLocal(TopologiaDoNo("vazio", ()))
