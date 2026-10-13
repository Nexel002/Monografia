import { describe, expect, it } from "vitest";
import { ajustarAoRetangulo, arrastar, caixaDosPontos, paraEcra, paraMundo, zoomar } from "./vista";

const caixa = { xMin: 0, yMin: 0, xMax: 200, yMax: 100 };

describe("ajustarAoRetangulo", () => {
  it("enquadra a caixa toda e centra-a", () => {
    const v = ajustarAoRetangulo(caixa, 400, 400);
    expect(v.escala).toBe(2); // limitada pela largura: 400 px / 200 m
    expect(paraEcra(v, 100, 50)).toEqual([200, 200]);
  });

  it("o y do mundo cresce para cima e o do ecrã para baixo", () => {
    const v = ajustarAoRetangulo(caixa, 400, 400);
    expect(paraEcra(v, 100, 90)[1]).toBeLessThan(paraEcra(v, 100, 10)[1]);
  });
});

describe("paraMundo / paraEcra", () => {
  it("são inversas uma da outra", () => {
    const v = { escala: 3, x0: 10, y0: 80 };
    const [px, py] = paraEcra(v, 55, 33);
    const [x, y] = paraMundo(v, px, py);
    expect(x).toBeCloseTo(55);
    expect(y).toBeCloseTo(33);
  });
});

describe("zoomar", () => {
  it("mantém o ponto debaixo do cursor no mesmo sítio do ecrã", () => {
    const v = { escala: 2, x0: 0, y0: 100 };
    const antes = paraMundo(v, 120, 80);
    const depois = zoomar(v, 1.5, 120, 80);
    expect(depois.escala).toBe(3);
    const [x, y] = paraMundo(depois, 120, 80);
    expect(x).toBeCloseTo(antes[0]);
    expect(y).toBeCloseTo(antes[1]);
  });

  it("respeita os limites de zoom", () => {
    expect(zoomar({ escala: 39, x0: 0, y0: 0 }, 10, 0, 0).escala).toBe(40);
    expect(zoomar({ escala: 0.03, x0: 0, y0: 0 }, 0.01, 0, 0).escala).toBe(0.02);
  });
});

describe("arrastar", () => {
  it("arrastar para a direita mostra o que estava mais à esquerda", () => {
    expect(arrastar({ escala: 2, x0: 100, y0: 100 }, 20, 0).x0).toBe(90);
  });
});

describe("caixaDosPontos", () => {
  it("devolve null sem pontos", () => expect(caixaDosPontos([])).toBeNull());
  it("alarga pela margem", () => {
    expect(caixaDosPontos([[0, 0], [10, 20]], 5)).toEqual({ xMin: -5, yMin: -5, xMax: 15, yMax: 25 });
  });
});
