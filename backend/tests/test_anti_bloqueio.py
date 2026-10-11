from gestao_trafego.comum.tipos import FaseVerde, LeituraDeFaixa, Movimento, OrdemDeModo, TopologiaDoNo
from gestao_trafego.controlo.coordenador.anti_bloqueio import CoordenadorAntiBloqueio, ParametrosDoCoordenador
from gestao_trafego.controlo.local.max_pressure import ControladorLocal, ParametrosLocais

# Corredor de dois nós em fila: A despeja em f1, que é a entrada de B; B despeja em f2 (saída da rede).
#   entrada_a -> [A] -> f1 -> [B] -> f2
TOPOLOGIAS = {
    "A": TopologiaDoNo("A", (FaseVerde(0, "G", (Movimento("entrada_a", "f1"),)),)),
    "B": TopologiaDoNo("B", (FaseVerde(0, "G", (Movimento("f1", "f2"),)),)),
}
PARAMETROS = ParametrosDoCoordenador(
    limiar_alto=0.6, limiar_baixo=0.35, limiar_propagacao=0.4, vedacao_maxima_s=45, alivio_s=20, peso_saida=2.0
)


def faixa(ocupacao: float, capacidade: float = 10) -> LeituraDeFaixa:
    return LeituraDeFaixa(veiculos=round(ocupacao * capacidade), parados=round(ocupacao * capacidade), capacidade=capacidade)


def leitura(f1=0.0, f2=0.0, entrada_a=0.0) -> dict[str, LeituraDeFaixa]:
    return {"entrada_a": faixa(entrada_a), "f1": faixa(f1), "f2": faixa(f2)}


def test_sem_saturacao_ninguem_recebe_ordens():
    c = CoordenadorAntiBloqueio(TOPOLOGIAS, PARAMETROS)

    assert c.passo(1, leitura(f1=0.3)) == {"A": OrdemDeModo(), "B": OrdemDeModo()}


def test_faixa_cheia_e_vedada_so_ao_no_que_a_alimenta():
    c = CoordenadorAntiBloqueio(TOPOLOGIAS, PARAMETROS)

    ordens = c.passo(1, leitura(f1=0.7))

    assert ordens["A"] == OrdemDeModo(frozenset({"f1"}), 2.0)
    assert ordens["B"] == OrdemDeModo()  # f1 é entrada de B, não saída


def test_histerese_mantem_a_vedacao_ate_a_faixa_esvaziar_bem():
    c = CoordenadorAntiBloqueio(TOPOLOGIAS, PARAMETROS)
    c.passo(1, leitura(f1=0.7))

    assert c.passo(2, leitura(f1=0.5))["A"].faixas_vedadas == {"f1"}  # abaixo do alto, acima do baixo
    assert c.passo(3, leitura(f1=0.3))["A"].faixas_vedadas == frozenset()


def test_bloqueio_propaga_se_para_montante():
    c = CoordenadorAntiBloqueio(TOPOLOGIAS, PARAMETROS)

    # f2 (saída de B) está cheia. f1 só está a 50 % (abaixo do limiar alto), mas B não a consegue
    # escoar para f2 -> f1 conta como bloqueada e A deixa de a alimentar.
    ordens = c.passo(1, leitura(f1=0.5, f2=0.7))

    assert ordens["B"].faixas_vedadas == {"f2"}
    assert ordens["A"].faixas_vedadas == {"f1"}


def test_propagacao_nao_vedaria_uma_faixa_quase_vazia():
    c = CoordenadorAntiBloqueio(TOPOLOGIAS, PARAMETROS)

    ordens = c.passo(1, leitura(f1=0.1, f2=0.7))

    assert ordens["A"] == OrdemDeModo()


def test_valvula_de_alivio_liberta_a_faixa_depois_de_vedada_demasiado_tempo():
    c = CoordenadorAntiBloqueio(TOPOLOGIAS, PARAMETROS)
    cheia = leitura(f1=0.9)
    c.passo(0, cheia)

    assert c.passo(45, cheia)["A"].faixas_vedadas == {"f1"}  # ainda dentro dos 45 s
    assert c.passo(46, cheia)["A"].faixas_vedadas == frozenset()  # alívio
    assert c.passo(65, cheia)["A"].faixas_vedadas == frozenset()  # alívio dura 20 s
    assert c.passo(66, cheia)["A"].faixas_vedadas == {"f1"}  # volta a vedar


# --- o controlador local obedece à ordem ---

TOPOLOGIA_COM_DUAS_FASES = TopologiaDoNo(
    "X",
    (
        FaseVerde(0, "Gr", (Movimento("a1", "b1"),)),
        FaseVerde(1, "rG", (Movimento("a2", "b2"),)),
    ),
)
PARAMETROS_LOCAIS = ParametrosLocais(verde_minimo_s=10, verde_maximo_s=60, amarelo_s=4, vermelho_maximo_s=120, histerese=0.1)


def lei_x(a1: int, a2: int) -> dict[str, LeituraDeFaixa]:
    return {n: faixa(v / 10) for n, v in {"a1": a1, "a2": a2, "b1": 0, "b2": 0}.items()}


def correr(c: ControladorLocal, ate_s: int, lei) -> str:
    estado = c.estado
    for t in range(1, ate_s + 1):
        estado = c.passo(t, lei)
    return estado


def test_fase_cuja_saida_esta_vedada_deixa_de_ser_candidata():
    c = ControladorLocal(TOPOLOGIA_COM_DUAS_FASES, PARAMETROS_LOCAIS)
    c.receber_ordem(OrdemDeModo(frozenset({"b2"}), 2.0))

    # a2 tem muito mais fila, mas só despeja em b2 (vedada): não ganha o verde.
    assert correr(c, 100, lei_x(a1=3, a2=10)) == "Gr"


def test_fase_aberta_que_passa_a_vedada_cede_o_verde_sem_esperar_pela_histerese():
    c = ControladorLocal(TOPOLOGIA_COM_DUAS_FASES, PARAMETROS_LOCAIS)
    lei = lei_x(a1=3, a2=2)
    correr(c, 12, lei)
    c.receber_ordem(OrdemDeModo(frozenset({"b1"}), 2.0))

    assert c.passo(13, lei) == "yr"


def test_se_todas_as_fases_estao_vedadas_a_ordem_e_ignorada():
    c = ControladorLocal(TOPOLOGIA_COM_DUAS_FASES, PARAMETROS_LOCAIS)
    c.receber_ordem(OrdemDeModo(frozenset({"b1", "b2"}), 2.0))

    # Sem candidatas, o cruzamento continua a funcionar como Max-Pressure normal.
    assert correr(c, 30, lei_x(a1=0, a2=10)) == "rG"


def test_ordem_neutra_repoe_o_comportamento_normal():
    c = ControladorLocal(TOPOLOGIA_COM_DUAS_FASES, PARAMETROS_LOCAIS)
    c.receber_ordem(OrdemDeModo(frozenset({"b2"}), 2.0))
    c.receber_ordem(OrdemDeModo())

    assert correr(c, 30, lei_x(a1=1, a2=10)) == "rG"
