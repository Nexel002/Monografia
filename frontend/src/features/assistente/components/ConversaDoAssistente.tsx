import { Mic, MicOff, Send, Volume2, VolumeX } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { TextoFormatado } from "../../../shared/ui/TextoFormatado";
import { mensagemDeErro } from "../../../shared/utils/mensagemDeErro";
import { usePergunta } from "../hooks/useAssistente";
import type { MensagemNoEcra } from "../types/assistente";
import { falar, ouvir, pararDeFalar, reconhecimentoDisponivel } from "../utils/voz";

const ROTULO_DAS_FERRAMENTAS: Record<string, string> = {
  comparar_configuracoes: "comparação das configurações",
  precisao_da_previsao: "previsão",
  contagens_da_visao: "visão computacional",
  procura_por_via: "procura por via",
  indicadores_de_risco: "colisões simuladas",
  momentos_de_pico: "momentos de pico",
};

interface Props {
  perguntasSugeridas: string[];
}

let proximoId = 1;

export function ConversaDoAssistente({ perguntasSugeridas }: Props) {
  const [mensagens, setMensagens] = useState<MensagemNoEcra[]>([]);
  const [texto, setTexto] = useState("");
  const [aOuvir, setAOuvir] = useState(false);
  const [lerEmVozAlta, setLerEmVozAlta] = useState(false);
  const [erroDeVoz, setErroDeVoz] = useState<string | null>(null);
  const pergunta = usePergunta();
  const fim = useRef<HTMLDivElement>(null);
  const parar = useRef<(() => void) | null>(null);
  const microfone = reconhecimentoDisponivel();

  // Com chavetas: o React exige que um efeito não devolva nada além de uma função de limpeza, e `scrollIntoView`
  // devolve um valor nalguns browsers. Sem isto, a página inteira ficava em branco.
  useEffect(() => {
    fim.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensagens, pergunta.isPending]);
  useEffect(() => () => pararDeFalar(), []);

  const enviar = (perguntaDoUtilizador: string) => {
    const limpa = perguntaDoUtilizador.trim();
    if (!limpa || pergunta.isPending) return;
    // O histórico que o servidor recebe são só as trocas anteriores, sem a pergunta actual (essa vai à parte).
    const historico = mensagens.map(({ papel, texto: t }) => ({ papel, texto: t }));
    setMensagens((m) => [...m, { id: proximoId++, papel: "utilizador", texto: limpa }]);
    setTexto("");
    setErroDeVoz(null);
    pergunta.mutate(
      { pergunta: limpa, historico },
      {
        onSuccess: (resposta) => {
          setMensagens((m) => [...m, { id: proximoId++, papel: "assistente", texto: resposta.texto, resposta }]);
          if (lerEmVozAlta) void falar(resposta.texto);
        },
      },
    );
  };

  const alternarMicrofone = () => {
    if (aOuvir) {
      parar.current?.();
      return;
    }
    setErroDeVoz(null);
    pararDeFalar(); // não ouvir a própria voz
    parar.current = ouvir(
      (t) => enviar(t),
      () => setAOuvir(false),
      (m) => setErroDeVoz(m),
    );
    setAOuvir(parar.current !== null);
  };

  return (
    <div className="conversa">
      <div className="conversa-mensagens" role="log" aria-live="polite" aria-label="Conversa com o assistente">
        {mensagens.length === 0 && (
          <div className="conversa-vazia">
            <p>Pergunta-me sobre os resultados do sistema. Respondo com os números das simulações e dos vídeos, e digo sempre o que não está provado.</p>
            <div className="sugestoes">
              {perguntasSugeridas.map((p) => (
                <button key={p} onClick={() => enviar(p)}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}
        {mensagens.map((m) => (
          <div key={m.id} className={`balao ${m.papel}`}>
            <div className="balao-texto">{m.papel === "assistente" ? <TextoFormatado texto={m.texto} /> : m.texto}</div>
            {m.resposta && (
              <div className="balao-meta">
                <span className={`etiqueta ${m.resposta.modo}`}>{m.resposta.modo === "gemini" ? "Gemini" : "Modo de segurança"}</span>
                {[...new Set(m.resposta.ferramentas_usadas)].map((f) => (
                  <span key={f} className="etiqueta">
                    {ROTULO_DAS_FERRAMENTAS[f] ?? f}
                  </span>
                ))}
                <button className="icone" onClick={() => void falar(m.texto)} aria-label="Ouvir esta resposta" title="Ouvir esta resposta">
                  <Volume2 size={14} />
                </button>
              </div>
            )}
            {m.resposta?.aviso && <div className="balao-aviso">{m.resposta.aviso}</div>}
          </div>
        ))}
        {pergunta.isPending && <div className="balao assistente a-pensar" role="status">A consultar os resultados…</div>}
        {pergunta.isError && (
          <div className="estado-mensagem erro" role="alert">
            <div>
              <strong>Não consegui responder</strong>
              {mensagemDeErro(pergunta.error)}
            </div>
          </div>
        )}
        <div ref={fim} />
      </div>

      {erroDeVoz && <p className="nota" role="alert">{erroDeVoz}</p>}
      <form
        className="conversa-entrada"
        onSubmit={(e) => {
          e.preventDefault();
          enviar(texto);
        }}
      >
        <input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Escreve uma pergunta…" maxLength={1000} aria-label="A tua pergunta" />
        <button
          type="button"
          className={aOuvir ? "primario" : ""}
          onClick={alternarMicrofone}
          disabled={!microfone}
          aria-pressed={aOuvir}
          title={microfone ? (aOuvir ? "A ouvir… clica para parar" : "Falar") : "Este browser não suporta reconhecimento de voz (usa o Chrome ou o Edge)"}
          aria-label="Falar a pergunta"
        >
          {aOuvir ? <MicOff size={16} /> : <Mic size={16} />}
        </button>
        <button type="button" onClick={() => setLerEmVozAlta((v) => !v)} aria-pressed={lerEmVozAlta} title="Ler as respostas em voz alta" aria-label="Ler as respostas em voz alta">
          {lerEmVozAlta ? <Volume2 size={16} /> : <VolumeX size={16} />}
        </button>
        <button className="primario" type="submit" disabled={!texto.trim() || pergunta.isPending}>
          <Send size={16} /> Enviar
        </button>
      </form>
    </div>
  );
}
