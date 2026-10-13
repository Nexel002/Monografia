import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { configuracaoPorId } from "../../../shared/config/configuracoes";
import { COR_DA_GRELHA, ESTILO_DA_DICA, ESTILO_DOS_EIXOS } from "../../../shared/ui/estiloDeGrafico";
import { marcasDeTempo } from "../../../shared/utils/eixos";
import { formatarTempo } from "../../../shared/utils/formatar";
import type { AmostraDaSerie } from "../types/resultados";

export interface SerieNomeada {
  configuracao: string;
  amostras: AmostraDaSerie[];
}

/** Junta as séries por instante: uma linha por tempo, uma coluna por configuração. */
export function juntarSeries(series: SerieNomeada[]): Record<string, number>[] {
  const porTempo = new Map<number, Record<string, number>>();
  for (const { configuracao, amostras } of series) {
    for (const a of amostras) {
      const linha = porTempo.get(a.tempo_s) ?? { tempo_s: a.tempo_s };
      linha[configuracao] = a.veiculos_parados;
      porTempo.set(a.tempo_s, linha);
    }
  }
  return [...porTempo.values()].sort((a, b) => a.tempo_s - b.tempo_s);
}

export function GraficoDeSerie({ series }: { series: SerieNomeada[] }) {
  const dados = juntarSeries(series);
  return (
    <div style={{ height: 320 }}>
      <ResponsiveContainer>
        <LineChart data={dados} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={COR_DA_GRELHA} vertical={false} />
          <XAxis dataKey="tempo_s" type="number" domain={[0, "dataMax"]} ticks={marcasDeTempo(dados.at(-1)?.tempo_s ?? 0)} tickFormatter={formatarTempo} {...ESTILO_DOS_EIXOS} />
          <YAxis width={40} {...ESTILO_DOS_EIXOS} />
          <Tooltip {...ESTILO_DA_DICA} labelFormatter={(t) => `Tempo ${formatarTempo(Number(t))}`} />
          <Legend />
          {series.map(({ configuracao }) => {
            const config = configuracaoPorId(configuracao);
            return <Line key={configuracao} type="monotone" dataKey={configuracao} name={config.curto} stroke={config.cor} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />;
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
