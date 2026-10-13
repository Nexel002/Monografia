import { Bar, BarChart, CartesianGrid, Cell, ErrorBar, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { configuracaoPorId } from "../../../shared/config/configuracoes";
import { COR_DA_GRELHA, ESTILO_DA_DICA, ESTILO_DOS_EIXOS } from "../../../shared/ui/estiloDeGrafico";
import { formatarDecimal } from "../../../shared/utils/formatar";
import type { LinhaDaComparacao } from "../types/resultados";

export function GraficoDeEspera({ linhas }: { linhas: LinhaDaComparacao[] }) {
  const dados = linhas.map((l) => ({
    nome: configuracaoPorId(l.configuracao).curto,
    cor: configuracaoPorId(l.configuracao).cor,
    espera: l.espera_media_s,
    desvio: l.espera_desvio_s ?? 0,
  }));
  return (
    <div style={{ height: 300 }}>
      <ResponsiveContainer>
        <BarChart data={dados} margin={{ top: 22, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={COR_DA_GRELHA} vertical={false} />
          <XAxis dataKey="nome" interval={0} {...ESTILO_DOS_EIXOS} />
          <YAxis width={40} unit=" s" {...ESTILO_DOS_EIXOS} />
          <Tooltip
            {...ESTILO_DA_DICA}
            cursor={{ fill: "var(--superficie-2)" }}
            formatter={(valor) => [`${formatarDecimal(Number(valor))} s`, "Espera média"]}
          />
          {/* barras finas, com cantos arredondados no topo; uma cor por configuração (a mesma em todo o dashboard) */}
          <Bar dataKey="espera" radius={[4, 4, 0, 0]} maxBarSize={56}>
            {dados.map((d) => (
              <Cell key={d.nome} fill={d.cor} />
            ))}
            <ErrorBar dataKey="desvio" stroke="var(--tinta-2)" strokeWidth={1.5} width={6} />
            <LabelList dataKey="espera" position="insideTop" formatter={(v: unknown) => formatarDecimal(Number(v), 0)} fill="#ffffff" fontSize={13} fontWeight={600} offset={8} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
