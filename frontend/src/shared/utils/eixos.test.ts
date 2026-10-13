import { describe, expect, it } from "vitest";
import { marcasDeTempo } from "./eixos";

describe("marcasDeTempo", () => {
  it("dá marcas redondas de 10 em 10 minutos", () => expect(marcasDeTempo(1500)).toEqual([0, 600, 1200]));
  it("inclui o máximo quando é múltiplo do passo", () => expect(marcasDeTempo(1200)).toEqual([0, 600, 1200]));
  it("com máximo inválido devolve só o zero", () => {
    expect(marcasDeTempo(0)).toEqual([0]);
    expect(marcasDeTempo(Number.NaN)).toEqual([0]);
  });
  it("com passo inválido não entra em ciclo infinito", () => expect(marcasDeTempo(100, 0)).toEqual([0]));
});
