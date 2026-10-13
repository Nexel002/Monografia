import { describe, expect, it } from "vitest";
import type { VeiculoDetectado } from "../types/aoVivo";
import { extrapolarCaixas } from "./extrapolar";

const carro = (id: number, x: number, y: number): VeiculoDetectado => [id, x, y, x + 40, y + 20, "carro", 0];

describe("extrapolarCaixas", () => {
  it("sem análise anterior devolve as caixas como estão", () => {
    const actual = { veiculos: [carro(1, 10, 10)], t: 1 };
    expect(extrapolarCaixas(null, actual, 1.2)).toBe(actual.veiculos);
  });

  it("avança a caixa à velocidade medida entre as duas análises", () => {
    // 20 px em 0,1 s = 200 px/s; passaram 0,05 s desde a última análise -> +10 px
    const [c] = extrapolarCaixas({ veiculos: [carro(1, 0, 0)], t: 0.9 }, { veiculos: [carro(1, 20, 40)], t: 1 }, 1.05);
    expect(c[1]).toBeCloseTo(30);
    expect(c[2]).toBeCloseTo(60);
    expect(c[3]).toBeCloseTo(70); // a caixa inteira desloca-se, não só o canto
  });

  it("limita a extrapolação ao máximo", () => {
    const [c] = extrapolarCaixas({ veiculos: [carro(1, 0, 0)], t: 0 }, { veiculos: [carro(1, 10, 0)], t: 1 }, 100, 0.5);
    expect(c[1]).toBeCloseTo(15); // 10 px/s × 0,5 s
  });

  it("não recua se o vídeo estiver antes da análise", () => {
    const actual = { veiculos: [carro(1, 20, 0)], t: 1 };
    expect(extrapolarCaixas({ veiculos: [carro(1, 0, 0)], t: 0.5 }, actual, 0.8)).toBe(actual.veiculos);
  });

  it("um veículo novo (sem histórico) fica onde foi visto", () => {
    const [c] = extrapolarCaixas({ veiculos: [carro(1, 0, 0)], t: 0.9 }, { veiculos: [carro(2, 50, 50)], t: 1 }, 1.05);
    expect(c[1]).toBe(50);
  });

  it("preserva o tipo e o estado de contado", () => {
    const contado: VeiculoDetectado = [1, 20, 0, 60, 20, "camiao", 1];
    const [c] = extrapolarCaixas({ veiculos: [carro(1, 0, 0)], t: 0.9 }, { veiculos: [contado], t: 1 }, 1.05);
    expect([c[5], c[6]]).toEqual(["camiao", 1]);
  });

  it("duas análises com o mesmo instante não dividem por zero", () => {
    const actual = { veiculos: [carro(1, 20, 0)], t: 1 };
    expect(extrapolarCaixas({ veiculos: [carro(1, 0, 0)], t: 1 }, actual, 1.1)).toBe(actual.veiculos);
  });
});
