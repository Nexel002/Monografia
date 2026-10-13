import { describe, expect, it } from "vitest";
import type { VeiculoMsg } from "../types/mensagens";
import { interpolarAngulo, interpolarVeiculos } from "./interpolar";

const carro = (id: string, x: number, y: number, angulo = 0, parado: 0 | 1 = 0): VeiculoMsg => [id, x, y, angulo, 0, parado];

describe("interpolarAngulo", () => {
  it("passa por 0° entre 350° e 10°", () => expect(interpolarAngulo(350, 10, 0.5)).toBeCloseTo(0));
  it("interpolação simples", () => expect(interpolarAngulo(10, 50, 0.5)).toBeCloseTo(30));
  it("nos extremos devolve os ângulos dados", () => {
    expect(interpolarAngulo(90, 180, 0)).toBeCloseTo(90);
    expect(interpolarAngulo(90, 180, 1)).toBeCloseTo(180);
  });
});

describe("interpolarVeiculos", () => {
  it("põe o veículo a meio caminho entre as duas posições", () => {
    const [v] = interpolarVeiculos([carro("a", 0, 0)], [carro("a", 10, 20)], 0.5);
    expect([v.x, v.y]).toEqual([5, 10]);
  });

  it("um veículo novo aparece na posição actual", () => {
    const [v] = interpolarVeiculos([carro("a", 0, 0)], [carro("b", 7, 8)], 0.3);
    expect([v.x, v.y]).toEqual([7, 8]);
  });

  it("sem mensagem anterior usa a posição actual", () => {
    const [v] = interpolarVeiculos(null, [carro("a", 3, 4)], 0.5);
    expect([v.x, v.y]).toEqual([3, 4]);
  });

  it("limita t ao intervalo [0, 1]", () => {
    const [v] = interpolarVeiculos([carro("a", 0, 0)], [carro("a", 10, 0)], 5);
    expect(v.x).toBe(10);
  });

  it("um veículo que já não existe deixa de aparecer", () => {
    expect(interpolarVeiculos([carro("a", 0, 0), carro("b", 1, 1)], [carro("b", 2, 2)], 1)).toHaveLength(1);
  });

  it("converte o campo parado em booleano", () => {
    expect(interpolarVeiculos(null, [carro("a", 0, 0, 0, 1)], 1)[0].parado).toBe(true);
  });
});
