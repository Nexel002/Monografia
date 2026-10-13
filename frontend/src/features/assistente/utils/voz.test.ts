import { describe, expect, it } from "vitest";
import { limparParaFala, mensagemDeErroDeVoz } from "./voz";

describe("limparParaFala", () => {
  it("tira o markdown", () => expect(limparParaFala("**Resultado** com `50 s`")).toBe("Resultado com 50 s"));

  it("transforma uma lista com travessões em frases separadas por pausas", () => {
    expect(limparParaFala("Resultados:\n- tempo fixo: 100 s\n- local: 75 s")).toBe("Resultados: tempo fixo: 100 s. local: 75 s");
  });

  it("não deixa pontos duplicados nem espaços a mais", () => {
    expect(limparParaFala("Fim.\n\n- outra   coisa")).toBe("Fim. outra coisa");
  });

  it("texto vazio dá texto vazio", () => expect(limparParaFala("  \n ")).toBe(""));
});

describe("mensagemDeErroDeVoz", () => {
  it("traduz os códigos conhecidos", () => expect(mensagemDeErroDeVoz("not-allowed")).toContain("microfone"));
  it("mostra o código desconhecido em vez de esconder o erro", () => expect(mensagemDeErroDeVoz("xpto")).toContain("xpto"));
});
