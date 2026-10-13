import type { VeiculoMsg } from "../types/mensagens";

export interface PosicaoDoVeiculo {
  x: number;
  y: number;
  angulo: number;
  tipo: number;
  parado: boolean;
}

/** Interpolação do ângulo pelo caminho mais curto: de 350° para 10° passa por 0°, não por 180°. */
export function interpolarAngulo(de: number, para: number, t: number): number {
  const diferenca = ((((para - de) % 360) + 540) % 360) - 180;
  return (de + diferenca * t + 360) % 360;
}

/**
 * Posição de cada veículo entre duas mensagens (t de 0 a 1). O servidor envia poucas vezes por segundo;
 * sem isto os carros saltavam dezenas de metros de cada vez. Um veículo que ainda não existia na
 * mensagem anterior aparece logo na posição actual.
 */
export function interpolarVeiculos(anterior: VeiculoMsg[] | null, actual: VeiculoMsg[], t: number): PosicaoDoVeiculo[] {
  const antes = new Map<string, VeiculoMsg>();
  anterior?.forEach((v) => antes.set(v[0], v));
  const f = Math.min(1, Math.max(0, t));
  return actual.map(([id, x, y, angulo, tipo, parado]) => {
    const a = antes.get(id);
    if (!a) return { x, y, angulo, tipo, parado: parado === 1 };
    return {
      x: a[1] + (x - a[1]) * f,
      y: a[2] + (y - a[2]) * f,
      angulo: interpolarAngulo(a[3], angulo, f),
      tipo,
      parado: parado === 1,
    };
  });
}
