const numero = (casas: number) => new Intl.NumberFormat("pt-PT", { minimumFractionDigits: casas, maximumFractionDigits: casas });

export const formatarDecimal = (valor: number, casas = 1): string => numero(casas).format(valor);
export const formatarInteiro = (valor: number): string => numero(0).format(Math.round(valor));
export const formatarPercentagem = (fraccao: number, casas = 0): string => `${numero(casas).format(fraccao * 100)} %`;

/** Variação relativa com sinal explícito: +12 % / −24 %. Usa o sinal menos tipográfico. */
export function formatarVariacao(fraccao: number): string {
  const texto = numero(0).format(Math.abs(fraccao * 100));
  return `${fraccao > 0 ? "+" : fraccao < 0 ? "−" : ""}${texto} %`;
}

export function formatarTempo(segundos: number): string {
  const total = Math.max(0, Math.round(segundos));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}
