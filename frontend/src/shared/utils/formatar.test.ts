import { describe, expect, it } from "vitest";
import { formatarTempo, formatarVariacao } from "./formatar";

describe("formatarVariacao", () => {
  it("mostra o sinal explícito", () => {
    expect(formatarVariacao(0.12)).toBe("+12 %");
    expect(formatarVariacao(-0.24)).toBe("−24 %");
  });
  it("não mostra sinal em zero", () => expect(formatarVariacao(0)).toBe("0 %"));
});

describe("formatarTempo", () => {
  it("formata minutos e segundos", () => expect(formatarTempo(125)).toBe("2:05"));
  it("não devolve tempo negativo", () => expect(formatarTempo(-3)).toBe("0:00"));
});
