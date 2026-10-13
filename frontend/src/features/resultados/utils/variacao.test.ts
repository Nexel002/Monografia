import { describe, expect, it } from "vitest";
import type { LinhaDaComparacao } from "../types/resultados";
import { variacaoFaceAoFixo } from "./variacao";

const linha = (configuracao: string, espera: number): LinhaDaComparacao => ({
  configuracao,
  sementes: 8,
  espera_media_s: espera,
  espera_desvio_s: 1,
  fila_media_veiculos: 1,
  velocidade_media_ms: 1,
  teleportes: 0,
});

describe("variacaoFaceAoFixo", () => {
  const linhas = [linha("fixo", 100), linha("local", 75), linha("pior", 130)];

  it("é negativa quando a espera desce", () => expect(variacaoFaceAoFixo(linhas, "local")).toBeCloseTo(-0.25));
  it("é positiva quando a espera sobe", () => expect(variacaoFaceAoFixo(linhas, "pior")).toBeCloseTo(0.3));
  it("o próprio tempo fixo não tem variação", () => expect(variacaoFaceAoFixo(linhas, "fixo")).toBeNull());
  it("sem tempo fixo na tabela não inventa uma referência", () => expect(variacaoFaceAoFixo([linha("local", 75)], "local")).toBeNull());
  it("configuração inexistente devolve null", () => expect(variacaoFaceAoFixo(linhas, "x")).toBeNull());
});
