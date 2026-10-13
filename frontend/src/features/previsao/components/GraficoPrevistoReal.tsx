import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { COR_DA_GRELHA, ESTILO_DA_DICA, ESTILO_DOS_EIXOS } from "../../../shared/ui/estiloDeGrafico";
import { marcasDeTempo } from "../../../shared/utils/eixos";
import { formatarTempo } from "../../../shared/utils/formatar";
import type { PontoDaPrevisao } from "../types/previsao";

export function GraficoPrevistoReal({ pontos }: { pontos: PontoDaPrevisao[] }) {
  return (
    <div style={{ height: 320 }}>
      <ResponsiveContainer>
        <LineChart data={pontos} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={COR_DA_GRELHA} vertical={false} />
          <XAxis dataKey="tempo_s" type="number" domain={[0, "dataMax"]} ticks={marcasDeTempo(pontos.at(-1)?.tempo_s ?? 0)} tickFormatter={formatarTempo} {...ESTILO_DOS_EIXOS} />
          <YAxis width={40} {...ESTILO_DOS_EIXOS} />
          <Tooltip {...ESTILO_DA_DICA} labelFormatter={(t) => `Tempo ${formatarTempo(Number(t))}`} formatter={(v) => Number(v).toFixed(1)} />
          <Legend />
          <Line type="monotone" dataKey="real" name="Real" stroke="var(--tinta-2)" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="previsto" name="Previsto (LSTM)" stroke="var(--acento)" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
