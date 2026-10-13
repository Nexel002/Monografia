import { API_URL } from "../config/api";
import { textoDoDetalhe } from "../utils/mensagemDeErro";

export class ErroDaApi extends Error {
  constructor(
    mensagem: string,
    readonly estado: number,
  ) {
    super(mensagem);
  }
}

/** GET que devolve JSON tipado. Um erro HTTP vira `ErroDaApi` com a mensagem já legível. */
export async function obter<T>(caminho: string, parametros?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(API_URL + caminho);
  for (const [chave, valor] of Object.entries(parametros ?? {})) {
    if (valor !== undefined) url.searchParams.set(chave, String(valor));
  }
  let resposta: Response;
  try {
    resposta = await fetch(url);
  } catch {
    // fetch só rejeita por falha de rede: a API está desligada ou o endereço está errado
    throw new ErroDaApi(`Não foi possível ligar à API em ${API_URL}. O servidor está a correr?`, 0);
  }
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => ({}));
    throw new ErroDaApi(textoDoDetalhe((corpo as { detail?: unknown }).detail), resposta.status);
  }
  return resposta.json() as Promise<T>;
}
