import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { COR_DA_GRELHA, ESTILO_DA_DICA, ESTILO_DOS_EIXOS } from "../../../shared/ui/estiloDeGrafico";
import { formatarTempo } from "../../../shared/utils/formatar";
import { ROTULO_DO_TIPO, TIPOS_DE_VEICULO, type JanelaDeContagem } from "../types/visao";

const COR_DO_TIPO: Record<string, string> = {
  carro: "var(--tipo-carro)",
  mota: "var(--tipo-mota)",
  autocarro: "var(--tipo-autocarro)",
  camiao: "var(--tipo-camiao)",
};

export function GraficoDeFluxo({ janelas }: { janelas: JanelaDeContagem[] }) {
  const dados = janelas.map((j) => ({ inicio_s: j.inicio_s, ...Object.fromEntries(TIPOS_DE_VEICULO.map((t) => [t, j.por_tipo[t] ?? 0])) }));
  return (
    <div style={{ height: 280 }}>
      <ResponsiveContainer>
        <BarChart data={dados} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={COR_DA_GRELHA} vertical={false} />
          <XAxis dataKey="inicio_s" tickFormatter={formatarTempo} {...ESTILO_DOS_EIXOS} />
          <YAxis width={36} allowDecimals={false} {...ESTILO_DOS_EIXOS} />
          <Tooltip {...ESTILO_DA_DICA} cursor={{ fill: "var(--superficie-2)" }} labelFormatter={(t) => `Janela a partir de ${formatarTempo(Number(t))}`} />
          <Legend />
          {/* barras empilhadas com 2 px de separação da cor da superfície, para os segmentos não se fundirem */}
          {TIPOS_DE_VEICULO.map((tipo) => (
            <Bar key={tipo} dataKey={tipo} name={ROTULO_DO_TIPO[tipo]} stackId="tipos" fill={COR_DO_TIPO[tipo]} stroke="var(--superficie)" strokeWidth={2} maxBarSize={44} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function GraficoDeFila({ janelas }: { janelas: JanelaDeContagem[] }) {
  return (
    <div style={{ height: 220 }}>
      <ResponsiveContainer>
        <LineChart data={janelas} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={COR_DA_GRELHA} vertical={false} />
          <XAxis dataKey="inicio_s" tickFormatter={formatarTempo} {...ESTILO_DOS_EIXOS} />
          <YAxis width={36} {...ESTILO_DOS_EIXOS} />
          <Tooltip {...ESTILO_DA_DICA} labelFormatter={(t) => `Janela a partir de ${formatarTempo(Number(t))}`} formatter={(v) => [Number(v).toFixed(1), "Fila média"]} />
          <Line type="monotone" dataKey="fila_media_veiculos" name="Fila média" stroke="var(--acento)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
