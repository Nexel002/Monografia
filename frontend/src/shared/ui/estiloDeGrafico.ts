// Estilo partilhado dos gráficos (Recharts): tinta secundária nos eixos, grelha quase invisível.
export const ESTILO_DOS_EIXOS = { stroke: "var(--tinta-3)", fontSize: 12 } as const;
export const COR_DA_GRELHA = "var(--linha)";
export const ESTILO_DA_DICA = {
  contentStyle: { background: "var(--superficie-2)", border: "1px solid var(--eixo)", borderRadius: 8, color: "var(--tinta)", fontSize: 13 },
  labelStyle: { color: "var(--tinta-2)" },
  itemStyle: { color: "var(--tinta)" },
  cursor: { stroke: "var(--tinta-3)", strokeDasharray: "3 3" },
} as const;
