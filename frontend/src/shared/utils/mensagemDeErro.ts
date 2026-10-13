// A API (FastAPI) devolve `detail` como texto num 404 e como LISTA de objectos num 422 de validação.
// Mostrar o corpo em bruto daria «[object Object]» no ecrã do utilizador.
export function mensagemDeErro(erro: unknown): string {
  if (erro instanceof Error) return erro.message;
  if (typeof erro === "string") return erro;
  return "Ocorreu um erro inesperado.";
}

export function textoDoDetalhe(detalhe: unknown): string {
  if (typeof detalhe === "string") return detalhe;
  if (Array.isArray(detalhe)) {
    return detalhe
      .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
      .join("; ");
  }
  return "Pedido inválido.";
}
