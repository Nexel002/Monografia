// Transformação entre as coordenadas do SUMO (metros, y para cima) e o ecrã (píxeis, y para baixo).

export interface Vista {
  /** píxeis por metro */
  escala: number;
  /** posição, em metros, do ponto que fica no canto superior esquerdo do ecrã */
  x0: number;
  y0: number;
}

export interface Caixa {
  xMin: number;
  yMin: number;
  xMax: number;
  yMax: number;
}

/** Vista que enquadra `caixa` (com uma margem em metros) centrada num ecrã de largura × altura px. */
export function ajustarAoRetangulo(caixa: Caixa, largura: number, altura: number, margem = 0): Vista {
  const larguraM = caixa.xMax - caixa.xMin + 2 * margem;
  const alturaM = caixa.yMax - caixa.yMin + 2 * margem;
  const escala = Math.min(largura / larguraM, altura / alturaM);
  const centroX = (caixa.xMin + caixa.xMax) / 2;
  const centroY = (caixa.yMin + caixa.yMax) / 2;
  return { escala, x0: centroX - largura / (2 * escala), y0: centroY + altura / (2 * escala) };
}

export function paraEcra(vista: Vista, x: number, y: number): [number, number] {
  return [(x - vista.x0) * vista.escala, (vista.y0 - y) * vista.escala];
}

export function paraMundo(vista: Vista, px: number, py: number): [number, number] {
  return [vista.x0 + px / vista.escala, vista.y0 - py / vista.escala];
}

/** Zoom que mantém fixo o ponto do mundo que está debaixo do cursor (px, py). */
export function zoomar(vista: Vista, factor: number, px: number, py: number, minimo = 0.02, maximo = 40): Vista {
  const escala = Math.min(maximo, Math.max(minimo, vista.escala * factor));
  const [mx, my] = paraMundo(vista, px, py);
  return { escala, x0: mx - px / escala, y0: my + py / escala };
}

export function arrastar(vista: Vista, dxPx: number, dyPx: number): Vista {
  return { ...vista, x0: vista.x0 - dxPx / vista.escala, y0: vista.y0 + dyPx / vista.escala };
}

/** Caixa que contém todos os pontos, alargada de `margem` metros. */
export function caixaDosPontos(pontos: [number, number][], margem = 0): Caixa | null {
  if (pontos.length === 0) return null;
  const xs = pontos.map((p) => p[0]);
  const ys = pontos.map((p) => p[1]);
  return { xMin: Math.min(...xs) - margem, yMin: Math.min(...ys) - margem, xMax: Math.max(...xs) + margem, yMax: Math.max(...ys) + margem };
}
