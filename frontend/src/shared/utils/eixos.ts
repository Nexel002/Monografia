/** Marcas de tempo «redondas» (de `passo` em `passo` segundos) para um eixo que vai de 0 até `maximo`. */
export function marcasDeTempo(maximo: number, passo = 600): number[] {
  if (!Number.isFinite(maximo) || maximo <= 0 || passo <= 0) return [0];
  const marcas: number[] = [];
  for (let t = 0; t <= maximo; t += passo) marcas.push(t);
  return marcas;
}
