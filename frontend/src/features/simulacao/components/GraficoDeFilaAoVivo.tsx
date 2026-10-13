import { CartesianGrid, Legend, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { COR_DA_GRELHA, ESTILO_DA_DICA, ESTILO_DOS_EIXOS } from "../../../shared/ui/estiloDeGrafico";
import { marcasDeTempo } from "../../../shared/utils/eixos";
import { formatarTempo } from "../../../shared/utils/formatar";
import { configuracaoPorId } from "../../../shared/config/configuracoes";
import type { PontoDoHistorico } from "../hooks/useSimulacaoAoVivo";
import type { Lado } from "../types/mensagens";

interface Props {
  historico: PontoDoHistorico[];
  configuracoes: Record<Lado, string> | null;
  /** [início, fim] do incidente em segundos, para sombrear no gráfico. */
  incidente: [number, number] | null;
}

export function GraficoDeFilaAoVivo({ historico, configuracoes, incidente }: Props) {
  const esquerda = configuracaoPorId(configuracoes?.esquerda ?? "fixo");
  const direita = configuracaoPorId(configuracoes?.direita ?? "coordenado+vias");
  return (
    <div style={{ height: 240 }}>
      <ResponsiveContainer>
        <LineChart data={historico} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={COR_DA_GRELHA} vertical={false} />
          <XAxis dataKey="t" type="number" domain={[0, "dataMax"]} ticks={marcasDeTempo(historico.at(-1)?.t ?? 0, 300)} tickFormatter={formatarTempo} {...ESTILO_DOS_EIXOS} />
          <YAxis width={40} {...ESTILO_DOS_EIXOS} />
          <Tooltip {...ESTILO_DA_DICA} labelFormatter={(t) => `Tempo ${formatarTempo(Number(t))}`} />
          <Legend />
          {incidente && <ReferenceArea x1={incidente[0]} x2={incidente[1]} fill="var(--critico)" fillOpacity={0.12} label={{ value: "incidente", fill: "var(--tinta-3)", fontSize: 11 }} />}
          <Line type="monotone" dataKey="esquerda" name={esquerda.curto} stroke={esquerda.cor} strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="direita" name={direita.curto} stroke={direita.cor} strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
