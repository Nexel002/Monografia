import { Pause, Play, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Cartao } from "../../../shared/ui/Cartao";
import { EstadoDaConsulta } from "../../../shared/ui/EstadoDaConsulta";
import { formatarDecimal, formatarInteiro } from "../../../shared/utils/formatar";
import { enderecoDoVideoOriginal } from "../api/visaoApi";
import { useVideos } from "../hooks/useVisao";
import { useVisaoAoVivo } from "../hooks/useVisaoAoVivo";
import { ROTULO_DO_TIPO, TIPOS_DE_VEICULO } from "../types/visao";
import { extrapolarCaixas } from "../utils/extrapolar";

const DURACOES: { rotulo: string; segundos: number | null }[] = [
  { rotulo: "10 s", segundos: 10 },
  { rotulo: "30 s", segundos: 30 },
  { rotulo: "60 s", segundos: 60 },
  { rotulo: "Todo", segundos: null },
];
const TAMANHOS_DE_IMAGEM = [320, 480, 640];

const VERDE = "#0ca30c";
const AMARELO = "#fab219";

/** Só os quatro cantos da caixa: mais limpo do que um rectângulo inteiro com muitos veículos. */
function desenharCantos(ctx: CanvasRenderingContext2D, x1: number, y1: number, x2: number, y2: number) {
  const cx = Math.max(6, (x2 - x1) / 4);
  const cy = Math.max(6, (y2 - y1) / 4);
  ctx.beginPath();
  for (const [x, y, dx, dy] of [[x1, y1, 1, 1], [x2, y1, -1, 1], [x1, y2, 1, -1], [x2, y2, -1, -1]] as const) {
    ctx.moveTo(x + dx * cx, y);
    ctx.lineTo(x, y);
    ctx.lineTo(x, y + dy * cy);
  }
  ctx.stroke();
}

export function VisaoAoVivo() {
  const videos = useVideos();
  const videoRef = useRef<HTMLVideoElement>(null);
  const tela = useRef<HTMLCanvasElement>(null);
  const visao = useVisaoAoVivo(videoRef);
  const [escolhido, setEscolhido] = useState<string | null>(null);
  const [duracao, setDuracao] = useState<number | null>(10);
  const [imgsz, setImgsz] = useState(480);
  const [proporcao, setProporcao] = useState("16 / 9");

  const nomeDoVideo = escolhido ?? videos.data?.[0]?.nome ?? null;
  const ocupado = visao.estado === "a-preparar" || visao.estado === "a-correr" || visao.estado === "pausada";

  // Desenha por cima do vídeo, a cada fotograma do browser, as caixas que o servidor mandou.
  // Lê tudo de refs (vídeo, deteções): o React não re-renderiza ~10 vezes por segundo por causa disto.
  useEffect(() => {
    const canvas = tela.current;
    const video = videoRef.current;
    if (!canvas || !video) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let identificador = 0;

    const desenhar = () => {
      identificador = requestAnimationFrame(desenhar);
      const dpr = window.devicePixelRatio || 1;
      const largura = canvas.clientWidth;
      const altura = canvas.clientHeight;
      if (canvas.width !== Math.round(largura * dpr) || canvas.height !== Math.round(altura * dpr)) {
        canvas.width = Math.round(largura * dpr);
        canvas.height = Math.round(altura * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, largura, altura);

      const info = visao.info;
      const { actual, anterior } = visao.deteccoes.current;
      if (!info) return;
      const escala = largura / info.largura;

      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(info.linha[0] * escala, info.linha[1] * escala);
      ctx.lineTo(info.linha[2] * escala, info.linha[3] * escala);
      ctx.stroke();

      if (!actual) return;
      const veiculos = extrapolarCaixas(
        anterior ? { veiculos: anterior.veiculos, t: anterior.t_video } : null,
        { veiculos: actual.veiculos, t: actual.t_video },
        video.currentTime,
      );
      ctx.lineWidth = 2;
      ctx.font = "600 11px system-ui, sans-serif";
      for (const [id, x1, y1, x2, y2, tipo, contado] of veiculos) {
        const cor = contado ? VERDE : AMARELO;
        ctx.strokeStyle = cor;
        desenharCantos(ctx, x1 * escala, y1 * escala, x2 * escala, y2 * escala);
        ctx.fillStyle = cor;
        ctx.beginPath(); // ponto de contagem: a base da caixa
        ctx.arc(((x1 + x2) / 2) * escala, y2 * escala, 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillText(`${tipo} #${id}`, x1 * escala, Math.max(10, y1 * escala - 4));
      }
    };
    identificador = requestAnimationFrame(desenhar);
    return () => cancelAnimationFrame(identificador);
  }, [visao.info, visao.deteccoes]);

  return (
    <div className="grelha grelha-2" style={{ gridTemplateColumns: "minmax(0, 1.6fr) minmax(0, 1fr)" }}>
      <Cartao titulo="Vídeo com o algoritmo a trabalhar">
        <div className="barra-de-controlos" style={{ marginBottom: 12 }}>
          <label className="campo">
            Vídeo
            <select value={nomeDoVideo ?? ""} onChange={(e) => setEscolhido(e.target.value)} disabled={ocupado || !videos.data?.length}>
              {(videos.data ?? []).map((v) => (
                <option key={v.nome} value={v.nome}>{v.nome.replace(".webm", "")}</option>
              ))}
            </select>
          </label>
          <div className="campo">
            Duração
            <div className="segmentado" role="group" aria-label="Duração a analisar">
              {DURACOES.map((d) => (
                <button key={d.rotulo} aria-pressed={duracao === d.segundos} disabled={ocupado} onClick={() => setDuracao(d.segundos)}>
                  {d.rotulo}
                </button>
              ))}
            </div>
          </div>
          <label className="campo">
            Imagem do detector
            <select value={imgsz} onChange={(e) => setImgsz(Number(e.target.value))} disabled={ocupado}>
              {TAMANHOS_DE_IMAGEM.map((t) => (
                <option key={t} value={t}>{t} px{t === 480 ? " (recomendado)" : ""}</option>
              ))}
            </select>
          </label>
          <div style={{ flex: 1 }} />
          {ocupado ? (
            <>
              <button onClick={visao.alternarPausa} disabled={visao.estado === "a-preparar"}>
                {visao.estado === "pausada" ? <Play size={16} /> : <Pause size={16} />}
                {visao.estado === "pausada" ? "Retomar" : "Pausa"}
              </button>
              <button onClick={visao.parar}>
                <Square size={16} /> Parar
              </button>
            </>
          ) : (
            <button className="primario" disabled={!nomeDoVideo} onClick={() => nomeDoVideo && visao.iniciar({ video: nomeDoVideo, segundos: duracao, imgsz })}>
              <Play size={16} /> {visao.estado === "terminada" ? "Repetir" : "Iniciar"}
            </button>
          )}
        </div>

        <div className="video-caixa" style={{ aspectRatio: proporcao }}>
          {nomeDoVideo && (
            <video
              ref={videoRef}
              key={nomeDoVideo}
              className="video-original"
              src={enderecoDoVideoOriginal(nomeDoVideo)}
              preload="auto"
              muted
              playsInline
              onLoadedMetadata={(e) => setProporcao(`${e.currentTarget.videoWidth} / ${e.currentTarget.videoHeight}`)}
            />
          )}
          <canvas ref={tela} className="video-sobreposicao" aria-hidden />
          {visao.estado === "a-preparar" && (
            <div className="video-aviso" role="status">
              A carregar o modelo e a aquecer o detector… (alguns segundos)
            </div>
          )}
          {visao.estado === "parada" && <div className="video-aviso">Carrega em «Iniciar»: o vídeo corre e o algoritmo desenha por cima o que vê.</div>}
        </div>

        {visao.estado === "erro" && (
          <div className="estado-mensagem erro" role="alert" style={{ marginTop: 12 }}>
            <div>
              <strong>A análise parou</strong>
              {visao.erro}
            </div>
          </div>
        )}
        <div className="legenda" style={{ marginTop: 12 }}>
          <span><i className="ponto" style={{ background: AMARELO }} /> ainda por contar</span>
          <span><i className="ponto" style={{ background: VERDE }} /> já contado</span>
          <span><i className="ponto" style={{ background: "#fff" }} /> ponto de contagem (base da caixa) e linha</span>
        </div>
      </Cartao>

      <Cartao titulo="Contagem ao vivo">
        <EstadoDaConsulta consulta={videos} vazio={(v) => v.length === 0} mensagemVazia="Não há vídeos em dados/videos/." alturaDoEsqueleto={200}>
          {() => (
            <>
              <div className="indicadores">
                <div className="indicador">
                  <span>Veículos contados</span>
                  <strong>{visao.totais ? formatarInteiro(visao.totais.total) : "—"}</strong>
                </div>
                {TIPOS_DE_VEICULO.map((t) => (
                  <div className="indicador" key={t}>
                    <span>{ROTULO_DO_TIPO[t]}</span>
                    <strong>{visao.totais ? formatarInteiro(visao.totais.por_tipo[t] ?? 0) : "—"}</strong>
                  </div>
                ))}
                <div className="indicador">
                  <span>Análises por segundo</span>
                  <strong>{visao.metricas ? formatarDecimal(visao.metricas.analisesPorS) : "—"}</strong>
                  <small>o vídeo tem 30 fotogramas/s</small>
                </div>
                <div className="indicador">
                  <span>Atraso de cada análise</span>
                  <strong>
                    {visao.metricas ? formatarInteiro(visao.metricas.latenciaMs) : "—"}
                    <small> ms</small>
                  </strong>
                </div>
              </div>
              {visao.estado === "terminada" && visao.resumo && (
                <p className="nota">
                  Terminou: {formatarInteiro(visao.resumo.total)} veículos contados em {formatarInteiro(visao.resumo.analises)} análises
                  ({formatarInteiro(visao.resumo.fotogramas_lidos)} fotogramas lidos).
                </p>
              )}
              <p className="nota">
                O vídeo corre aqui, no browser, sem abrandar. O servidor analisa o fotograma mais recente de cada vez, por isso vê só uma parte
                dos fotogramas e pode contar menos do que o processamento completo (separador «Contagem completa»), que é a referência.
                A precisão ainda não está medida contra uma contagem manual.
              </p>
            </>
          )}
        </EstadoDaConsulta>
      </Cartao>
    </div>
  );
}
