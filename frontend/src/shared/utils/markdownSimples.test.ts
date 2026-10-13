import { describe, expect, it } from "vitest";
import { analisarInline, analisarMarkdown } from "./markdownSimples";

describe("analisarInline", () => {
  it("separa negrito e código do texto normal", () => {
    expect(analisarInline("a **b** e `c` d")).toEqual([{ texto: "a " }, { texto: "b", negrito: true }, { texto: " e " }, { texto: "c", codigo: true }, { texto: " d" }]);
  });
  it("asteriscos soltos ficam como texto", () => expect(analisarInline("2 * 3 = 6")).toEqual([{ texto: "2 * 3 = 6" }]));
});

describe("analisarMarkdown", () => {
  it("reconhece títulos, parágrafos e a linha horizontal", () => {
    const blocos = analisarMarkdown("### Resultado\nTexto numa\nlinha só.\n\n---\nFim");
    expect(blocos.map((b) => b.tipo)).toEqual(["titulo", "paragrafo", "regra", "paragrafo"]);
    expect(blocos[0]).toMatchObject({ tipo: "titulo", nivel: 3 });
    expect(blocos[1]).toMatchObject({ segmentos: [{ texto: "Texto numa linha só." }] });
  });

  it("agrupa itens consecutivos numa só lista", () => {
    const [lista] = analisarMarkdown("* **A:** um\n* **B:** dois");
    expect(lista).toMatchObject({ tipo: "lista", ordenada: false });
    expect(lista.tipo === "lista" && lista.itens).toHaveLength(2);
  });

  it("distingue listas ordenadas de listas com marcas", () => {
    expect(analisarMarkdown("1. um\n2. dois")[0]).toMatchObject({ tipo: "lista", ordenada: true });
    expect(analisarMarkdown("- um\n- dois")[0]).toMatchObject({ tipo: "lista", ordenada: false });
  });

  it("uma lista ordenada a seguir a uma com marcas é outra lista", () => {
    expect(analisarMarkdown("- a\n1. b").map((b) => b.tipo)).toEqual(["lista", "lista"]);
  });

  it("HTML na resposta fica como texto (nunca é interpretado)", () => {
    const [p] = analisarMarkdown("<script>alert(1)</script>");
    expect(p).toMatchObject({ tipo: "paragrafo", segmentos: [{ texto: "<script>alert(1)</script>" }] });
  });

  it("texto vazio não dá blocos", () => expect(analisarMarkdown("  \n\n ")).toEqual([]));
});
