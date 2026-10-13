import { describe, expect, it } from "vitest";
import { CENARIOS, cenarioPorId } from "./cenarios";

describe("CENARIOS", () => {
  it("não repete identificadores nem combinações de incidente e escala", () => {
    expect(new Set(CENARIOS.map((c) => c.id)).size).toBe(CENARIOS.length);
    expect(new Set(CENARIOS.map((c) => `${c.incidente}-${c.escala}`)).size).toBe(CENARIOS.length);
  });

  it("a hora normal é metade do tráfego e sem incidente", () => {
    expect(cenarioPorId("normal")).toMatchObject({ escala: 0.5, incidente: false });
  });

  it("um identificador desconhecido cai no primeiro cenário em vez de rebentar", () => {
    expect(cenarioPorId("inventado" as never)).toBe(CENARIOS[0]);
  });
});
