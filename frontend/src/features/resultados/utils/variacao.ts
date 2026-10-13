import type { LinhaDaComparacao } from "../types/resultados";

/** Variação relativa de um valor face ao do tempo fixo (a referência). Sem referência, não há variação. */
export function variacaoFaceAoFixo(linhas: LinhaDaComparacao[], configuracao: string): number | null {
  const fixo = linhas.find((l) => l.configuracao === "fixo");
  const linha = linhas.find((l) => l.configuracao === configuracao);
  if (!fixo || !linha || fixo.espera_media_s === 0 || configuracao === "fixo") return null;
  return linha.espera_media_s / fixo.espera_media_s - 1;
}
