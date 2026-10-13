import type { VeiculoDetectado } from "../types/aoVivo";

/** Posição estimada das caixas no instante `agora`, a partir das duas últimas análises (tempos em segundos de vídeo).
 *
 * O servidor analisa ~10 vezes por segundo e o vídeo mostra 30: entre duas análises as caixas ficavam paradas
 * e depois saltavam. Cada caixa avança à velocidade que o veículo mostrou entre as duas últimas análises.
 * É só apresentação: a contagem usa sempre as posições reais do detector. `maximo` (s) limita a extrapolação:
 * passado isso é palpite, e é melhor parar a caixa do que deixá-la fugir. */
export function extrapolarCaixas(
  anterior: { veiculos: VeiculoDetectado[]; t: number } | null,
  actual: { veiculos: VeiculoDetectado[]; t: number },
  agora: number,
  maximo = 0.5,
): VeiculoDetectado[] {
  const passo = Math.min(Math.max(agora - actual.t, 0), maximo);
  const dt = anterior ? actual.t - anterior.t : 0;
  if (!anterior || dt <= 0.001 || passo === 0) return actual.veiculos;

  const antes = new Map(anterior.veiculos.map((v) => [v[0], v]));
  return actual.veiculos.map((v) => {
    const a = antes.get(v[0]);
    if (!a) return v;
    const dx = (((v[1] + v[3]) / 2 - (a[1] + a[3]) / 2) / dt) * passo;
    const dy = (((v[2] + v[4]) / 2 - (a[2] + a[4]) / 2) / dt) * passo;
    return [v[0], v[1] + dx, v[2] + dy, v[3] + dx, v[4] + dy, v[5], v[6]];
  });
}
