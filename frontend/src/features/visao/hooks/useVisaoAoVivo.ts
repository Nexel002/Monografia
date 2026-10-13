import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { WS_URL } from "../../../shared/config/api";
import type {
  InfoDaVisao,
  MensagemDaVisao,
  MensagemDeDeteccoes,
  ParametrosDaVisaoAoVivo,
  ResumoFinal,
  TotaisDaContagem,
} from "../types/aoVivo";
import { enderecoDoVideoOriginal } from "../api/visaoApi";

export type EstadoDaVisao = "parada" | "a-preparar" | "a-correr" | "pausada" | "terminada" | "erro";

export interface UltimasDeteccoes {
  actual: MensagemDeDeteccoes | null;
  anterior: MensagemDeDeteccoes | null;
}

const INTERVALO_DE_SINCRONIZACAO_MS = 1000;

/** Liga o vídeo do browser ao algoritmo do servidor: o vídeo corre aqui, as caixas vêm de lá. */
export function useVisaoAoVivo(videoRef: RefObject<HTMLVideoElement | null>) {
  const [estado, setEstado] = useState<EstadoDaVisao>("parada");
  const [erro, setErro] = useState<string | null>(null);
  const [info, setInfo] = useState<InfoDaVisao | null>(null);
  const [totais, setTotais] = useState<TotaisDaContagem | null>(null);
  const [metricas, setMetricas] = useState<{ analisesPorS: number; latenciaMs: number } | null>(null);
  const [resumo, setResumo] = useState<ResumoFinal | null>(null);
  // As deteções vão num ref: chegam ~10 vezes por segundo e quem desenha lê-as a cada fotograma sem re-renderizar.
  const deteccoes = useRef<UltimasDeteccoes>({ actual: null, anterior: null });
  const ligacao = useRef<WebSocket | null>(null);
  const temporizador = useRef<number | null>(null);
  const infoRef = useRef<InfoDaVisao | null>(null);

  const limparTemporizador = useCallback(() => {
    if (temporizador.current !== null) window.clearInterval(temporizador.current);
    temporizador.current = null;
  }, []);

  const enviar = useCallback((comando: object) => {
    if (ligacao.current?.readyState === WebSocket.OPEN) ligacao.current.send(JSON.stringify(comando));
  }, []);

  const parar = useCallback(() => {
    limparTemporizador();
    const ws = ligacao.current;
    ligacao.current = null; // antes de fechar: o onclose desta ligação já não pode mexer no estado
    if (ws && ws.readyState <= WebSocket.OPEN) {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ accao: "parar" }));
      ws.close();
    }
    videoRef.current?.pause();
  }, [limparTemporizador, videoRef]);

  useEffect(() => parar, [parar]); // ao sair da página fecha a ligação (e o servidor liberta o modelo)

  const aoReceber = useCallback(
    async (mensagem: MensagemDaVisao) => {
      switch (mensagem.tipo) {
        case "a_preparar":
          setEstado("a-preparar");
          break;
        case "pronto": {
          const { tipo: _tipo, ...informacao } = mensagem;
          void _tipo;
          infoRef.current = informacao;
          setInfo(informacao);
          const video = videoRef.current;
          if (!video) return;
          video.currentTime = 0;
          video.muted = true; // sem som: o browser só deixa arrancar sozinho um vídeo silencioso
          try {
            await video.play();
          } catch {
            setErro("O browser não deixou arrancar o vídeo. Carrega em «Retomar».");
            setEstado("pausada");
            return;
          }
          enviar({ accao: "iniciar", t: video.currentTime });
          setEstado("a-correr");
          // O relógio do servidor acerta-se pelo do vídeo: dois relógios independentes afastar-se-iam.
          temporizador.current = window.setInterval(() => {
            const v = videoRef.current;
            if (!v) return;
            enviar({ accao: "sincronizar", t: v.currentTime });
            const limite = infoRef.current?.ate_s;
            if (limite && v.currentTime >= limite) v.pause(); // o servidor termina por si e envia «fim»
          }, INTERVALO_DE_SINCRONIZACAO_MS);
          break;
        }
        case "deteccoes":
          deteccoes.current = { actual: mensagem, anterior: deteccoes.current.actual };
          setTotais(mensagem.totais);
          setMetricas({ analisesPorS: mensagem.analises_por_s, latenciaMs: mensagem.latencia_media_ms });
          break;
        case "fim":
          limparTemporizador();
          setResumo(mensagem.resumo);
          setTotais({ total: mensagem.resumo.total, por_tipo: mensagem.resumo.por_tipo, por_sentido: mensagem.resumo.por_sentido });
          videoRef.current?.pause();
          setEstado("terminada");
          break;
        case "erro":
          limparTemporizador();
          setErro(mensagem.mensagem);
          videoRef.current?.pause();
          setEstado("erro");
          break;
      }
    },
    [enviar, limparTemporizador, videoRef],
  );

  const iniciar = useCallback(
    (parametros: ParametrosDaVisaoAoVivo) => {
      parar();
      deteccoes.current = { actual: null, anterior: null };
      setErro(null);
      setInfo(null);
      setTotais(null);
      setMetricas(null);
      setResumo(null);
      setEstado("a-preparar");

      const consulta = new URLSearchParams({ video: parametros.video, imgsz: String(parametros.imgsz) });
      if (parametros.segundos) consulta.set("segundos", String(parametros.segundos));
      const ws = new WebSocket(`${WS_URL}/ws/visao?${consulta}`);
      ligacao.current = ws;
      ws.onmessage = (evento) => void aoReceber(JSON.parse(evento.data as string) as MensagemDaVisao);
      ws.onerror = () => {
        setErro(`Não foi possível ligar à API em ${WS_URL}. O servidor está a correr?`);
        setEstado("erro");
      };
      ws.onclose = () => {
        if (ligacao.current !== ws) return; // uma ligação antiga a fechar não pode mexer no estado da nova
        ligacao.current = null;
        limparTemporizador();
        setEstado((actual) => (actual === "a-correr" || actual === "a-preparar" || actual === "pausada" ? "erro" : actual));
        setErro((e) => e ?? "A ligação à API perdeu-se a meio da análise.");
      };
    },
    [aoReceber, limparTemporizador, parar],
  );

  const alternarPausa = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (estado === "a-correr") {
      video.pause();
      enviar({ accao: "pausar" });
      setEstado("pausada");
    } else if (estado === "pausada") {
      void video.play().then(() => {
        enviar({ accao: "retomar", t: video.currentTime });
        setErro(null);
        setEstado("a-correr");
      });
    }
  }, [enviar, estado, videoRef]);

  const enderecoDoVideo = (nome: string) => enderecoDoVideoOriginal(nome);

  return { estado, erro, info, totais, metricas, resumo, deteccoes, iniciar, parar, alternarPausa, enderecoDoVideo };
}
