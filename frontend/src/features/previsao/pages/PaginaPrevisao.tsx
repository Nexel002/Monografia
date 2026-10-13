import { useMemo, useState } from "react";
import { configuracaoPorId } from "../../../shared/config/configuracoes";
import { Cartao } from "../../../shared/ui/Cartao";
import { EstadoDaConsulta } from "../../../shared/ui/EstadoDaConsulta";
import { Pastilha } from "../../../shared/ui/Pastilha";
import { formatarDecimal, formatarVariacao } from "../../../shared/utils/formatar";
import { useExecucoes } from "../../resultados/hooks/useResultados";
import { GraficoPrevistoReal } from "../components/GraficoPrevistoReal";
import { useMetricas, usePrevisao } from "../hooks/usePrevisao";
import type { MetricasDaPrevisao } from "../types/previsao";

const HORIZONTES_S = [60, 180, 300];

function Metricas({ metricas }: { metricas: MetricasDaPrevisao }) {
  return (
    <>
      <div className="indicadores">
        {metricas.por_horizonte.map((h) => (
          <div className="indicador" key={h.horizonte_s}>
            <span>Daqui a {h.horizonte_s / 60} min</span>
            <strong className={h.melhoria_percentual > 0 ? "melhor" : "pior"}>{formatarVariacao(-h.melhoria_percentual / 100)}</strong>
            <small>
              erro {formatarDecimal(h.mae_lstm_veiculos)} contra {formatarDecimal(h.mae_persistencia_veiculos)} veíc. (persistência)
            </small>
          </div>
        ))}
      </div>
      <h3 style={{ margin: "18px 0 8px", fontSize: 14, color: "var(--tinta-2)" }}>Por configuração (erro em veículos, LSTM / persistência)</h3>
      <table>
        <thead>
          <tr>
            <th>Configuração</th>
            {HORIZONTES_S.map((h) => (
              <th key={h}>{h / 60} min</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Object.entries(metricas.por_configuracao).map(([configuracao, horizontes]) => {
            const config = configuracaoPorId(configuracao);
            return (
              <tr key={configuracao}>
                <td>
                  <span className="com-pastilha">
                    <Pastilha cor={config.cor} />
                    {config.rotulo}
                  </span>
                </td>
                {horizontes.map((h) => (
                  <td key={h.horizonte_s} className={h.mae_lstm_veiculos < h.mae_persistencia_veiculos ? "melhor" : "pior"}>
                    {formatarDecimal(h.mae_lstm_veiculos)} / {formatarDecimal(h.mae_persistencia_veiculos)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}

export function PaginaPrevisao() {
  const metricas = useMetricas();
  const execucoes = useExecucoes();
  const [horizonte, setHorizonte] = useState(60);
  const [escolhida, setEscolhida] = useState<number | null>(null);

  // Só as execuções de teste têm previsões guardadas (as de treino não servem para avaliar).
  const doTeste = useMemo(
    () => (execucoes.data ?? []).filter((e) => metricas.data?.sementes_de_teste.includes(e.semente) && e.escala === 1),
    [execucoes.data, metricas.data],
  );
  const execucaoId = escolhida !== null && doTeste.some((e) => e.id === escolhida) ? escolhida : (doTeste[0]?.id ?? null);
  const previsao = usePrevisao(execucaoId, horizonte);

  return (
    <>
      <div className="titulo-de-pagina">
        <div>
          <h1>Previsão de congestionamento</h1>
          <p>
            Um LSTM olha para os últimos 5 minutos da rede (veículos parados, veículos na rede, velocidade) e prevê quantos veículos
            estarão parados daqui a 1, 3 e 5 minutos. Compara-se com a previsão mais simples possível: «daqui a pouco estará igual a agora».
          </p>
        </div>
      </div>

      <Cartao titulo="Erro do modelo no conjunto de teste">
        <EstadoDaConsulta consulta={metricas} alturaDoEsqueleto={220} mensagemVazia="O modelo ainda não foi treinado.">
          {(m) => (
            <>
              <Metricas metricas={m} />
              <p className="nota">
                Leitura honesta: a melhoria é grande nos semáforos de <strong>tempo fixo</strong>, onde a fila segue o ciclo regular dos
                semáforos. Com controlo adaptativo o ganho é pequeno a 1 minuto e deixa de existir a 5 minutos. Treino em {m.execucoes_de_treino} execuções, teste em {m.execucoes_de_teste} (sementes {m.sementes_de_teste.join(" e ")}, que o modelo nunca viu).
              </p>
            </>
          )}
        </EstadoDaConsulta>
      </Cartao>

      <Cartao
        titulo="Previsto contra real"
        accao={
          <div className="barra-de-controlos">
            <label className="campo">
              Corrida
              <select value={execucaoId ?? ""} onChange={(e) => setEscolhida(Number(e.target.value))} disabled={doTeste.length === 0}>
                {doTeste.map((e) => (
                  <option key={e.id} value={e.id}>
                    {configuracaoPorId(e.configuracao).curto} · semente {e.semente}{e.incidente ? " · via cortada" : ""}
                  </option>
                ))}
              </select>
            </label>
            <div className="campo">
              Horizonte
              <div className="segmentado" role="group" aria-label="Horizonte da previsão">
                {HORIZONTES_S.map((h) => (
                  <button key={h} aria-pressed={horizonte === h} onClick={() => setHorizonte(h)}>
                    {h / 60} min
                  </button>
                ))}
              </div>
            </div>
          </div>
        }
      >
        {execucaoId === null ? (
          <div className="estado-mensagem">Sem execuções de teste. Treina o modelo e importa os resultados.</div>
        ) : (
          <EstadoDaConsulta consulta={previsao} vazio={(p) => p.length === 0} alturaDoEsqueleto={320}>
            {(pontos) => <GraficoPrevistoReal pontos={pontos} />}
          </EstadoDaConsulta>
        )}
      </Cartao>
    </>
  );
}
