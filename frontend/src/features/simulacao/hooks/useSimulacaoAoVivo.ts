import { useCallback, useEffect, useRef, useState } from "react";
import { WS_URL } from "../../../shared/config/api";
import type { IndicadoresMsg, Lado, MensagemDoServidor, ParametrosDaSimulacao, VeiculoMsg } from "../types/mensagens";

export type EstadoDaLigacao = "parada" | "a-ligar" | "a-correr" | "pausada" | "terminada" | "erro";

/** O que o mapa precisa de ler a cada fotograma. Vive num ref: actualizá-lo não re-renderiza o React. */
export interface FonteDoLado {
  anterior: VeiculoMsg[] | null;
  actual: VeiculoMsg[];
  semaforos: Record<string, string>;
  chegouEm: number;
  intervaloMs: number;
}

export interface PontoDoHistorico {
  t: number;
  esquerda: number;
  direita: number;
}

const INTERVALO_DO_HISTORICO_S = 10;
const MAXIMO_DE_PONTOS = 600;

const fonteVazia = (): FonteDoLado => ({ anterior: null, actual: [], semaforos: {}, chegouEm: 0, intervaloMs: 250 });

export function useSimulacaoAoVivo() {
  const [estado, setEstado] = useState<EstadoDaLigacao>("parada");
  const [erro, setErro] = useState<string | null>(null);
  const [tempoS, setTempoS] = useState(0);
  const [indicadores, setIndicadores] = useState<Record<Lado, IndicadoresMsg> | null>(null);
  const [configuracoes, setConfiguracoes] = useState<Record<Lado, string> | null>(null);
  const [historico, setHistorico] = useState<PontoDoHistorico[]>([]);
  const fontes = useRef<Record<Lado, FonteDoLado>>({ esquerda: fonteVazia(), direita: fonteVazia() });
  const ligacao = useRef<WebSocket | null>(null);
  const terminadoPeloUtilizador = useRef(false);
  const ultimoPontoS = useRef(-INTERVALO_DO_HISTORICO_S);

  const fechar = useCallback(() => {
    terminadoPeloUtilizador.current = true;
    ligacao.current?.close();
    ligacao.current = null;
  }, []);

  useEffect(() => fechar, [fechar]); // ao sair da página, fecha a ligação (e o servidor fecha os SUMO)

  const processar = useCallback((mensagem: MensagemDoServidor) => {
    switch (mensagem.tipo) {
      case "inicio":
        setConfiguracoes(mensagem.configuracoes);
        setEstado("a-correr");
        break;
      case "estado": {
        const agora = performance.now();
        for (const lado of ["esquerda", "direita"] as const) {
          const f = fontes.current[lado];
          const dados = mensagem[lado];
          // média móvel do intervalo entre mensagens: é o tempo que o mapa leva a interpolar até à seguinte
          const decorrido = f.chegouEm ? Math.min(1000, Math.max(50, agora - f.chegouEm)) : f.intervaloMs;
          fontes.current[lado] = {
            anterior: f.actual.length ? f.actual : null,
            actual: dados.v,
            semaforos: dados.s,
            chegouEm: agora,
            intervaloMs: f.intervaloMs * 0.6 + decorrido * 0.4,
          };
        }
        setTempoS(mensagem.t);
        setIndicadores({ esquerda: mensagem.esquerda.k, direita: mensagem.direita.k });
        if (mensagem.t - ultimoPontoS.current >= INTERVALO_DO_HISTORICO_S) {
          ultimoPontoS.current = mensagem.t;
          setHistorico((h) =>
            [...h, { t: mensagem.t, esquerda: mensagem.esquerda.k.parados, direita: mensagem.direita.k.parados }].slice(-MAXIMO_DE_PONTOS),
          );
        }
        break;
      }
      case "fim":
        setEstado("terminada");
        break;
      case "erro":
        setErro(mensagem.mensagem);
        setEstado("erro");
        break;
    }
  }, []);

  const iniciar = useCallback(
    (parametros: ParametrosDaSimulacao) => {
      fechar();
      terminadoPeloUtilizador.current = false;
      fontes.current = { esquerda: fonteVazia(), direita: fonteVazia() };
      ultimoPontoS.current = -INTERVALO_DO_HISTORICO_S;
      setHistorico([]);
      setIndicadores(null);
      setTempoS(0);
      setErro(null);
      setEstado("a-ligar");

      const consulta = new URLSearchParams({
        semente: String(parametros.semente),
        velocidade: String(parametros.velocidade),
        incidente: String(parametros.incidente),
        esquerda: parametros.esquerda,
        direita: parametros.direita,
      });
      const ws = new WebSocket(`${WS_URL}/ws/simulacao?${consulta}`);
      ligacao.current = ws;
      ws.onmessage = (evento) => processar(JSON.parse(evento.data as string) as MensagemDoServidor);
      ws.onerror = () => {
        setErro(`Não foi possível ligar à API em ${WS_URL}. O servidor está a correr?`);
        setEstado("erro");
      };
      ws.onclose = () => {
        if (ligacao.current !== ws) return; // uma ligação antiga a fechar não pode mexer no estado da nova
        ligacao.current = null;
        setEstado((actual) => (actual === "a-correr" || actual === "pausada" ? (terminadoPeloUtilizador.current ? "parada" : "erro") : actual));
        if (!terminadoPeloUtilizador.current) setErro((e) => e ?? "A ligação à API perdeu-se a meio da simulação.");
      };
    },
    [fechar, processar],
  );

  const enviar = useCallback((comando: object) => {
    if (ligacao.current?.readyState === WebSocket.OPEN) ligacao.current.send(JSON.stringify(comando));
  }, []);

  const parar = useCallback(() => {
    fechar();
    setEstado("parada");
  }, [fechar]);

  // Lê o estado do fecho (e não dentro de um `setEstado(fn)`): o React pode invocar essa função duas
  // vezes em desenvolvimento, e o comando seria enviado duas vezes ao servidor.
  const alternarPausa = useCallback(() => {
    if (estado === "a-correr") {
      enviar({ accao: "pausa" });
      setEstado("pausada");
    } else if (estado === "pausada") {
      enviar({ accao: "retomar" });
      setEstado("a-correr");
    }
  }, [estado, enviar]);

  const mudarVelocidade = useCallback((valor: number) => enviar({ accao: "velocidade", valor }), [enviar]);

  return { estado, erro, tempoS, indicadores, configuracoes, historico, fontes, iniciar, parar, alternarPausa, mudarVelocidade };
}
