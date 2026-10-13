import { useMemo, useState } from "react";
import { CONFIGURACOES } from "../../../shared/config/configuracoes";
import { Cartao } from "../../../shared/ui/Cartao";
import { EstadoDaConsulta } from "../../../shared/ui/EstadoDaConsulta";
import { GraficoDeEspera } from "../components/GraficoDeEspera";
import { GraficoDeSerie } from "../components/GraficoDeSerie";
import { TabelaComparativa } from "../components/TabelaComparativa";
import { useComparacao, useExecucoes, useSeries } from "../hooks/useResultados";

export function PaginaResultados() {
  const [incidente, setIncidente] = useState(true);
  const [semente, setSemente] = useState<number | null>(null);
  const comparacao = useComparacao(incidente);
  const execucoes = useExecucoes();

  // Execuções da semente escolhida, uma por configuração, na ordem do estudo.
  const sementesDisponiveis = useMemo(
    () => [...new Set((execucoes.data ?? []).filter((e) => e.incidente === incidente).map((e) => e.semente))].sort((a, b) => a - b),
    [execucoes.data, incidente],
  );
  const sementeEscolhida = semente !== null && sementesDisponiveis.includes(semente) ? semente : (sementesDisponiveis[0] ?? null);
  const daSemente = useMemo(
    () =>
      CONFIGURACOES.flatMap((c) => {
        const e = (execucoes.data ?? []).find((x) => x.configuracao === c.id && x.semente === sementeEscolhida && x.incidente === incidente && x.escala === 1);
        return e ? [{ configuracao: c.id, id: e.id }] : [];
      }),
    [execucoes.data, sementeEscolhida, incidente],
  );
  const series = useSeries(daSemente.map((e) => e.id));
  const seriesProntas = series.every((s) => s.data) ? daSemente.map((e, i) => ({ configuracao: e.configuracao, amostras: series[i].data! })) : null;

  return (
    <>
      <div className="titulo-de-pagina">
        <div>
          <h1>Resultados da comparação</h1>
          <p>
            O mesmo tráfego, a mesma hora de ponta, cinco formas de controlar os semáforos. As médias usam só as sementes (conjuntos de
            veículos) que existem em todas as configurações, para a comparação ser justa.
          </p>
        </div>
        <div className="segmentado" role="group" aria-label="Cenário">
          <button aria-pressed={incidente} onClick={() => setIncidente(true)}>Hora de ponta + via cortada</button>
          <button aria-pressed={!incidente} onClick={() => setIncidente(false)}>Hora de ponta</button>
        </div>
      </div>

      <EstadoDaConsulta consulta={comparacao} vazio={(d) => d.length === 0} mensagemVazia="Sem resultados para este cenário. Importa as simulações com python -m gestao_trafego.dados.importar." alturaDoEsqueleto={320}>
        {(linhas) => (
          <>
            <div className="grelha grelha-2">
              <Cartao titulo="Espera média por veículo (menos é melhor)">
                <GraficoDeEspera linhas={linhas} />
                <p className="nota">A barra fina é o desvio-padrão entre sementes. Espera = tempo com o veículo parado.</p>
              </Cartao>
              <Cartao titulo="Tabela comparativa">
                <TabelaComparativa linhas={linhas} />
              </Cartao>
            </div>
          </>
        )}
      </EstadoDaConsulta>

      <Cartao
        titulo="Evolução dos veículos parados numa corrida"
        accao={
          <label className="campo" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            Semente
            <select value={sementeEscolhida ?? ""} onChange={(e) => setSemente(Number(e.target.value))} disabled={sementesDisponiveis.length === 0}>
              {sementesDisponiveis.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>
        }
      >
        <EstadoDaConsulta consulta={execucoes} vazio={(d) => d.length === 0} alturaDoEsqueleto={320}>
          {() =>
            seriesProntas ? (
              <GraficoDeSerie series={seriesProntas} />
            ) : series.some((s) => s.isError) ? (
              <div className="estado-mensagem erro" role="alert">Não foi possível carregar as séries desta corrida.</div>
            ) : (
              <div className="esqueleto" style={{ height: 320 }} role="status" aria-label="A carregar" />
            )
          }
        </EstadoDaConsulta>
        <p className="nota">Cada linha é uma configuração a correr os mesmos veículos. O pico é a hora de ponta; a via cortada começa aos 20 minutos.</p>
      </Cartao>
    </>
  );
}
