import { Maximize2, Pause, Play, Square } from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { CONFIGURACOES, configuracaoPorId } from "../../../shared/config/configuracoes";
import { Cartao } from "../../../shared/ui/Cartao";
import { EstadoDaConsulta } from "../../../shared/ui/EstadoDaConsulta";
import { formatarVariacao } from "../../../shared/utils/formatar";
import { GraficoDeFilaAoVivo } from "../components/GraficoDeFilaAoVivo";
import { IndicadoresDoLado } from "../components/IndicadoresDoLado";
import { MapaAoVivo } from "../components/MapaAoVivo";
import { useRede } from "../hooks/useRede";
import { useSimulacaoAoVivo } from "../hooks/useSimulacaoAoVivo";
import type { Rede } from "../types/mensagens";
import { ajustarAoRetangulo, caixaDosPontos, type Vista } from "../utils/vista";

const SEMENTES = [42, 7, 13, 1, 2, 3, 4, 5];
const VELOCIDADES = [5, 10, 20, 40];
// Igual a dados/cenarios/incidente_24_de_julho.json (início e duração do incidente simulado).
const INCIDENTE_S: [number, number] = [1200, 1800];
const CHEGADOS_MINIMOS_PARA_COMPARAR = 20;

const ESTADOS_COM_SIMULACAO = ["a-ligar", "a-correr", "pausada"];

function enquadramento(rede: Rede, largura: number, altura: number): Vista {
  // Enquadra a zona onde há semáforos (o corredor), não a rede inteira, que é muito maior.
  const centros = rede.semaforos.flatMap((s) => (s.centro ? [s.centro] : []));
  const caixa = caixaDosPontos(centros, 450);
  return ajustarAoRetangulo(caixa ?? { xMin: rede.limites.x_min, yMin: rede.limites.y_min, xMax: rede.limites.x_max, yMax: rede.limites.y_max }, largura, altura);
}

export function PaginaSimulacao() {
  const rede = useRede();
  const simulacao = useSimulacaoAoVivo();
  const [semente, setSemente] = useState(42);
  const [velocidade, setVelocidade] = useState(10);
  const [incidente, setIncidente] = useState(true);
  const [esquerda, setEsquerda] = useState("fixo");
  const [direita, setDireita] = useState("coordenado+vias");
  const [vista, setVista] = useState<Vista | null>(null);
  const tamanho = useRef<[number, number] | null>(null);

  const aCorrer = ESTADOS_COM_SIMULACAO.includes(simulacao.estado);
  const mesmaConfiguracao = esquerda === direita;

  const aoDimensionar = useCallback(
    (largura: number, altura: number) => {
      tamanho.current = [largura, altura];
      if (rede.data) setVista((v) => v ?? enquadramento(rede.data, largura, altura));
    },
    [rede.data],
  );
  const reenquadrar = () => tamanho.current && rede.data && setVista(enquadramento(rede.data, ...tamanho.current));

  const iniciar = () => simulacao.iniciar({ semente, velocidade, incidente, esquerda, direita });
  const escolherVelocidade = (v: number) => {
    setVelocidade(v);
    if (aCorrer) simulacao.mudarVelocidade(v);
  };

  // Média dos veículos parados desde o início: comparar só o instante actual dava saltos de centenas por cento.
  const mediaDaFila = useMemo(() => {
    const h = simulacao.historico;
    const media = (lado: "esquerda" | "direita") => (h.length ? h.reduce((soma, p) => soma + p[lado], 0) / h.length : 0);
    return { esquerda: media("esquerda"), direita: media("direita") };
  }, [simulacao.historico]);

  const comparacao = useMemo(() => {
    const i = simulacao.indicadores;
    if (!i || i.esquerda.chegados < CHEGADOS_MINIMOS_PARA_COMPARAR || i.direita.chegados < CHEGADOS_MINIMOS_PARA_COMPARAR) return null;
    return {
      espera: i.direita.espera_media_s / i.esquerda.espera_media_s - 1,
      parados: mediaDaFila.esquerda ? mediaDaFila.direita / mediaDaFila.esquerda - 1 : 0,
    };
  }, [simulacao.indicadores, mediaDaFila]);

  const configEsq = configuracaoPorId(simulacao.configuracoes?.esquerda ?? esquerda);
  const configDir = configuracaoPorId(simulacao.configuracoes?.direita ?? direita);

  return (
    <>
      <div className="titulo-de-pagina">
        <div>
          <h1>Simulação ao vivo</h1>
          <p>
            Duas simulações do corredor da Av. 24 de Julho, com os mesmos veículos a entrar à mesma hora. Só muda quem controla os
            semáforos. Vermelho = veículo parado.
          </p>
        </div>
      </div>

      <Cartao>
        <div className="barra-de-controlos">
          <label className="campo">
            Esquerda
            <select value={esquerda} onChange={(e) => setEsquerda(e.target.value)} disabled={aCorrer}>
              {CONFIGURACOES.map((c) => (
                <option key={c.id} value={c.id}>{c.rotulo}</option>
              ))}
            </select>
          </label>
          <label className="campo">
            Direita
            <select value={direita} onChange={(e) => setDireita(e.target.value)} disabled={aCorrer}>
              {CONFIGURACOES.map((c) => (
                <option key={c.id} value={c.id}>{c.rotulo}</option>
              ))}
            </select>
          </label>
          <label className="campo">
            Semente (tráfego)
            <select value={semente} onChange={(e) => setSemente(Number(e.target.value))} disabled={aCorrer}>
              {SEMENTES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="campo">
            Via cortada aos 20 min
            <select value={String(incidente)} onChange={(e) => setIncidente(e.target.value === "true")} disabled={aCorrer}>
              <option value="true">Sim</option>
              <option value="false">Não</option>
            </select>
          </label>
          <div className="campo">
            Velocidade
            <div className="segmentado" role="group" aria-label="Velocidade da simulação">
              {VELOCIDADES.map((v) => (
                <button key={v} aria-pressed={velocidade === v} onClick={() => escolherVelocidade(v)}>
                  {v}×
                </button>
              ))}
            </div>
          </div>
          <div style={{ flex: 1 }} />
          {aCorrer ? (
            <>
              <button onClick={simulacao.alternarPausa} disabled={simulacao.estado === "a-ligar"}>
                {simulacao.estado === "pausada" ? <Play size={16} /> : <Pause size={16} />}
                {simulacao.estado === "pausada" ? "Retomar" : "Pausa"}
              </button>
              <button onClick={simulacao.parar}>
                <Square size={16} /> Parar
              </button>
            </>
          ) : (
            <button className="primario" onClick={iniciar} disabled={mesmaConfiguracao || !rede.data}>
              <Play size={16} /> {simulacao.estado === "terminada" ? "Repetir" : "Iniciar"}
            </button>
          )}
          <button onClick={reenquadrar} title="Reenquadrar o mapa" aria-label="Reenquadrar o mapa">
            <Maximize2 size={16} />
          </button>
        </div>
        {mesmaConfiguracao && <p className="nota">Escolhe configurações diferentes à esquerda e à direita para comparar.</p>}
        {simulacao.estado === "a-ligar" && <p className="nota">A arrancar as duas simulações (alguns segundos)…</p>}
        {simulacao.estado === "terminada" && <p className="nota">Simulação terminada. «Repetir» começa de novo com os mesmos parâmetros.</p>}
        {simulacao.estado === "erro" && (
          <div className="estado-mensagem erro" role="alert" style={{ marginTop: 12 }}>
            <div>
              <strong>A simulação parou</strong>
              {simulacao.erro}
            </div>
          </div>
        )}
      </Cartao>

      <EstadoDaConsulta consulta={rede} alturaDoEsqueleto={420}>
        {(dadosDaRede) => (
          <>
            <div className="grelha grelha-2">
              {(["esquerda", "direita"] as const).map((lado) => {
                const config = lado === "esquerda" ? configEsq : configDir;
                const outro = lado === "esquerda" ? "direita" : "esquerda";
                return (
                  <Cartao key={lado}>
                    <MapaAoVivo
                      rede={dadosDaRede}
                      fontes={simulacao.fontes}
                      lado={lado}
                      vista={vista}
                      aoMudarVista={setVista}
                      aoDimensionar={aoDimensionar}
                      rotulo={config.rotulo}
                      cor={config.cor}
                      tempoS={simulacao.tempoS}
                    />
                    <div style={{ marginTop: 12 }}>
                      <IndicadoresDoLado
                        indicadores={simulacao.indicadores?.[lado] ?? null}
                        outro={simulacao.indicadores?.[outro] ?? null}
                      />
                    </div>
                  </Cartao>
                );
              })}
            </div>

            <div className="grelha grelha-2">
              <Cartao titulo="Quanto muda com o sistema da direita">
                {comparacao ? (
                  <div className="indicadores">
                    <div className="indicador">
                      <span>Espera média</span>
                      <strong className={comparacao.espera <= 0 ? "melhor" : "pior"}>{formatarVariacao(comparacao.espera)}</strong>
                      <small>da direita face à esquerda</small>
                    </div>
                    <div className="indicador">
                      <span>Fila média até agora</span>
                      <strong className={comparacao.parados <= 0 ? "melhor" : "pior"}>{formatarVariacao(comparacao.parados)}</strong>
                      <small>veículos parados, da direita face à esquerda</small>
                    </div>
                  </div>
                ) : (
                  <p className="nota">Aparece quando já chegaram {CHEGADOS_MINIMOS_PARA_COMPARAR} veículos ao destino em cada lado.</p>
                )}
                <div className="legenda" style={{ marginTop: 14 }}>
                  <span><i className="ponto" style={{ background: "var(--mapa-em-movimento)" }} /> veículo em movimento</span>
                  <span><i className="ponto" style={{ background: "var(--mapa-parado)" }} /> veículo parado</span>
                  <span><i className="ponto" style={{ background: "#0ca30c" }} /> <i className="ponto" style={{ background: "#fab219" }} /> <i className="ponto" style={{ background: "#e05252" }} /> sinal</span>
                  <span>✕ via cortada</span>
                </div>
                <p className="nota">Roda do rato para aproximar, arrastar para mover. Os dois mapas andam juntos.</p>
              </Cartao>
              <Cartao titulo="Veículos parados na rede">
                <GraficoDeFilaAoVivo historico={simulacao.historico} configuracoes={simulacao.configuracoes} incidente={incidente ? INCIDENTE_S : null} />
              </Cartao>
            </div>
          </>
        )}
      </EstadoDaConsulta>
    </>
  );
}
