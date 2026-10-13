import { sintetizarVoz } from "../api/assistenteApi";

/** Prepara um texto para ser lido em voz alta: sem markdown, com os travessões de listas como pausas. */
export function limparParaFala(texto: string): string {
  return texto
    .replace(/[*`#_]/g, "")
    .split("\n")
    .map((linha) => linha.replace(/^\s*[-•]\s*/, "").trim())
    .filter(Boolean)
    .join(". ")
    .replace(/\.\s*\./g, ".")
    .replace(/:\.\s/g, ": ") // «Resultados:. tempo fixo» → «Resultados: tempo fixo»
    .replace(/\s+/g, " ")
    .trim();
}

let audioActual: HTMLAudioElement | null = null;

export function pararDeFalar(): void {
  audioActual?.pause();
  audioActual = null;
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}

/**
 * Lê o texto em voz alta. Tenta primeiro a voz do servidor (mais natural); se não houver chaves ou o serviço
 * falhar, usa a voz do próprio browser, que não custa nada. Devolve a origem da voz usada.
 */
export async function falar(texto: string): Promise<"servidor" | "browser" | "nenhuma"> {
  pararDeFalar();
  const limpo = limparParaFala(texto);
  if (!limpo) return "nenhuma";
  try {
    const audio = await sintetizarVoz(limpo);
    if (audio) {
      const elemento = new Audio(URL.createObjectURL(audio));
      audioActual = elemento;
      elemento.onended = () => URL.revokeObjectURL(elemento.src);
      await elemento.play();
      return "servidor";
    }
  } catch {
    /* sem voz do servidor: cai para a do browser */
  }
  if (!("speechSynthesis" in window)) return "nenhuma";
  const fala = new SpeechSynthesisUtterance(limpo);
  fala.lang = "pt-PT";
  window.speechSynthesis.speak(fala);
  return "browser";
}

// --- reconhecimento de voz (o browser converte a fala em texto; não passa pelo nosso servidor) ---

interface ResultadoDeReconhecimento {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
}
interface Reconhecimento {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((e: ResultadoDeReconhecimento) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}
type ConstrutorDeReconhecimento = new () => Reconhecimento;

function construtor(): ConstrutorDeReconhecimento | null {
  const w = window as unknown as { SpeechRecognition?: ConstrutorDeReconhecimento; webkitSpeechRecognition?: ConstrutorDeReconhecimento };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export const reconhecimentoDisponivel = (): boolean => construtor() !== null;

const MENSAGENS_DE_ERRO: Record<string, string> = {
  "not-allowed": "O browser não deixou usar o microfone. Permite o acesso ao microfone para este site.",
  "service-not-allowed": "O reconhecimento de voz está bloqueado neste browser.",
  "no-speech": "Não ouvi nada. Tenta outra vez.",
  "audio-capture": "Não encontrei nenhum microfone.",
  network: "O reconhecimento de voz precisa de internet.",
};

export function mensagemDeErroDeVoz(codigo: string): string {
  return MENSAGENS_DE_ERRO[codigo] ?? `Erro no reconhecimento de voz (${codigo}).`;
}

/** Começa a ouvir. Devolve uma função que pára; null se o browser não suporta reconhecimento de voz. */
export function ouvir(aoReconhecer: (texto: string) => void, aoTerminar: () => void, aoFalhar: (mensagem: string) => void): (() => void) | null {
  const Construtor = construtor();
  if (!Construtor) return null;
  const reconhecimento = new Construtor();
  reconhecimento.lang = "pt-PT";
  reconhecimento.interimResults = false;
  reconhecimento.maxAlternatives = 1;
  reconhecimento.onresult = (e) => aoReconhecer(e.results[0][0].transcript);
  reconhecimento.onerror = (e) => aoFalhar(mensagemDeErroDeVoz(e.error));
  reconhecimento.onend = aoTerminar;
  reconhecimento.start();
  return () => reconhecimento.stop();
}
