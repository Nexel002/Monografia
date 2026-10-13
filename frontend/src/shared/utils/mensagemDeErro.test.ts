import { describe, expect, it } from "vitest";
import { mensagemDeErro, textoDoDetalhe } from "./mensagemDeErro";

describe("textoDoDetalhe", () => {
  it("devolve o texto de um detalhe simples", () => {
    expect(textoDoDetalhe("Não há série")).toBe("Não há série");
  });

  it("junta as mensagens de uma lista de validação em vez de mostrar [object Object]", () => {
    const detalhe = [{ msg: "valor inválido", loc: ["query", "escala"] }, { msg: "falta o campo" }];
    expect(textoDoDetalhe(detalhe)).toBe("valor inválido; falta o campo");
  });

  it("tem mensagem por omissão para formas desconhecidas", () => {
    expect(textoDoDetalhe(undefined)).toBe("Pedido inválido.");
  });
});

describe("mensagemDeErro", () => {
  it("lê a mensagem de um Error", () => expect(mensagemDeErro(new Error("falhou"))).toBe("falhou"));
  it("aceita texto", () => expect(mensagemDeErro("ups")).toBe("ups"));
  it("não rebenta com tipos estranhos", () => expect(mensagemDeErro(42)).toBe("Ocorreu um erro inesperado."));
});
