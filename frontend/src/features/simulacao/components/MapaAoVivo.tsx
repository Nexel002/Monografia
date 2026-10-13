import { useEffect, useRef, type RefObject } from "react";
import { formatarTempo } from "../../../shared/utils/formatar";
import { Pastilha } from "../../../shared/ui/Pastilha";
import type { FonteDoLado } from "../hooks/useSimulacaoAoVivo";
import { TIPO_AVARIADO, TIPO_CAMIAO, TIPO_CHAPA, TIPO_MOTA, type Lado, type Rede } from "../types/mensagens";
import { interpolarVeiculos } from "../utils/interpolar";
import { arrastar, paraEcra, zoomar, type Vista } from "../utils/vista";

interface Props {
  rede: Rede;
  fontes: RefObject<Record<Lado, FonteDoLado>>;
  lado: Lado;
  vista: Vista | null;
  aoMudarVista: (vista: Vista) => void;
  /** Chamado com o tamanho do mapa quando ainda não há vista: quem manda decide o enquadramento inicial. */
  aoDimensionar: (largura: number, altura: number) => void;
  rotulo: string;
  cor: string;
  tempoS: number;
}

// Comprimento de cada tipo de veículo em metros (o mesmo que a simulação usa).
const COMPRIMENTO_M: Record<number, number> = { 0: 4.5, [TIPO_CHAPA]: 6.5, [TIPO_MOTA]: 2.2, [TIPO_CAMIAO]: 9 };
const LARGURA_M: Record<number, number> = { 0: 1.9, [TIPO_CHAPA]: 2.1, [TIPO_MOTA]: 0.9, [TIPO_CAMIAO]: 2.5 };
const RUAS_PRINCIPAIS = /24 de Julho|Eduardo Mondlane/;

function corDoSinal(estado: string | undefined): string {
  switch (estado) {
    case "G":
    case "g":
      return "#0ca30c";
    case "y":
    case "Y":
      return "#fab219";
    case "r":
    case "R":
      return "#e05252";
    default:
      return "#898781";
  }
}

export function MapaAoVivo({ rede, fontes, lado, vista, aoMudarVista, aoDimensionar, rotulo, cor, tempoS }: Props) {
  const caixa = useRef<HTMLDivElement>(null);
  const tela = useRef<HTMLCanvasElement>(null);
  const vistaActual = useRef<Vista | null>(vista);
  const aoMudar = useRef(aoMudarVista);
  const aoDim = useRef(aoDimensionar);
  vistaActual.current = vista;
  aoMudar.current = aoMudarVista;
  aoDim.current = aoDimensionar;

  // Tamanho do canvas = tamanho do contentor × densidade de píxeis (nítido em ecrãs de alta resolução).
  useEffect(() => {
    const elemento = caixa.current;
    const canvas = tela.current;
    if (!elemento || !canvas) return;
    const ajustar = () => {
      const dpr = window.devicePixelRatio || 1;
      const { width, height } = elemento.getBoundingClientRect();
      canvas.width = Math.max(1, Math.round(width * dpr));
      canvas.height = Math.max(1, Math.round(height * dpr));
      if (width > 0 && height > 0) aoDim.current(width, height);
    };
    ajustar();
    const observador = new ResizeObserver(ajustar);
    observador.observe(elemento);
    return () => observador.disconnect();
  }, []);

  // Zoom com a roda e arrastar para mover. A roda precisa de um ouvinte não passivo para travar o scroll da página.
  useEffect(() => {
    const canvas = tela.current;
    if (!canvas) return;
    const aoRodar = (evento: WheelEvent) => {
      const v = vistaActual.current;
      if (!v) return;
      evento.preventDefault();
      const r = canvas.getBoundingClientRect();
      aoMudar.current(zoomar(v, evento.deltaY < 0 ? 1.2 : 1 / 1.2, evento.clientX - r.left, evento.clientY - r.top));
    };
    let ultimo: { x: number; y: number } | null = null;
    const aoPremir = (e: PointerEvent) => {
      ultimo = { x: e.clientX, y: e.clientY };
      canvas.setPointerCapture(e.pointerId);
    };
    const aoMover = (e: PointerEvent) => {
      const v = vistaActual.current;
      if (!ultimo || !v) return;
      aoMudar.current(arrastar(v, e.clientX - ultimo.x, e.clientY - ultimo.y));
      ultimo = { x: e.clientX, y: e.clientY };
    };
    const aoSoltar = () => (ultimo = null);
    canvas.addEventListener("wheel", aoRodar, { passive: false });
    canvas.addEventListener("pointerdown", aoPremir);
    canvas.addEventListener("pointermove", aoMover);
    canvas.addEventListener("pointerup", aoSoltar);
    canvas.addEventListener("pointercancel", aoSoltar);
    return () => {
      canvas.removeEventListener("wheel", aoRodar);
      canvas.removeEventListener("pointerdown", aoPremir);
      canvas.removeEventListener("pointermove", aoMover);
      canvas.removeEventListener("pointerup", aoSoltar);
      canvas.removeEventListener("pointercancel", aoSoltar);
    };
  }, []);

  // Ciclo de desenho: corre a cada fotograma do browser e lê o ref, por isso as mensagens do servidor
  // (3 a 6 por segundo) não obrigam o React a re-renderizar nem o mapa a saltar.
  useEffect(() => {
    const canvas = tela.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const estilo = getComputedStyle(document.documentElement);
    let identificador = 0;

    const desenhar = () => {
      identificador = requestAnimationFrame(desenhar);
      const v = vistaActual.current;
      if (!v) return;
      const dpr = window.devicePixelRatio || 1;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      const corRua = estilo.getPropertyValue("--mapa-rua").trim();
      const corPrincipal = estilo.getPropertyValue("--mapa-rua-principal").trim();
      for (const rua of rede.ruas) {
        ctx.strokeStyle = RUAS_PRINCIPAIS.test(rua.nome) ? corPrincipal : corRua;
        ctx.lineWidth = Math.max(1, rua.faixas * 3.2 * v.escala);
        ctx.beginPath();
        rua.pontos.forEach(([x, y], i) => {
          const [px, py] = paraEcra(v, x, y);
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        });
        ctx.stroke();
      }

      const fonte = fontes.current[lado];
      const t = fonte.intervaloMs > 0 ? (performance.now() - fonte.chegouEm) / fonte.intervaloMs : 1;
      const corMovimento = estilo.getPropertyValue("--mapa-em-movimento").trim();
      const corParado = estilo.getPropertyValue("--mapa-parado").trim();
      for (const veiculo of interpolarVeiculos(fonte.anterior, fonte.actual, t)) {
        const [px, py] = paraEcra(v, veiculo.x, veiculo.y);
        if (px < -20 || py < -20 || px > canvas.width / dpr + 20 || py > canvas.height / dpr + 20) continue;
        if (veiculo.tipo === TIPO_AVARIADO) {
          const r = Math.max(5, 4 * v.escala);
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(px - r, py - r);
          ctx.lineTo(px + r, py + r);
          ctx.moveTo(px + r, py - r);
          ctx.lineTo(px - r, py + r);
          ctx.stroke();
          continue;
        }
        // Tamanho mínimo em píxeis: à escala do corredor um carro real daria menos de 2 px e desaparecia.
        // Os parados saem um pouco maiores: é a fila que o olho tem de apanhar primeiro.
        const realce = veiculo.parado ? 1.3 : 1;
        const comprimento = Math.max(5.5, (COMPRIMENTO_M[veiculo.tipo] ?? 4.5) * v.escala) * realce;
        const largura = Math.max(3, (LARGURA_M[veiculo.tipo] ?? 1.9) * v.escala) * realce;
        ctx.save();
        ctx.translate(px, py);
        ctx.rotate((veiculo.angulo * Math.PI) / 180); // o ângulo do SUMO é horário a partir do norte, tal como o canvas
        ctx.fillStyle = veiculo.parado ? corParado : corMovimento;
        ctx.fillRect(-largura / 2, -comprimento / 2, largura, comprimento);
        ctx.restore();
      }

      // Sinais por cima de tudo, para se verem mesmo debaixo dos carros parados.
      const raio = Math.max(3.2, 2.6 * v.escala);
      for (const semaforo of rede.semaforos) {
        const estado = fonte.semaforos[semaforo.id];
        semaforo.sinais.forEach(([x, y], i) => {
          const [px, py] = paraEcra(v, x, y);
          ctx.fillStyle = corDoSinal(estado?.[i]);
          ctx.beginPath();
          ctx.arc(px, py, raio, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = "rgba(0,0,0,0.65)"; // anel escuro: o sinal lê-se por cima dos carros parados
          ctx.lineWidth = 1;
          ctx.stroke();
        });
      }
    };
    identificador = requestAnimationFrame(desenhar);
    return () => cancelAnimationFrame(identificador);
  }, [rede, fontes, lado]);

  return (
    <div className="mapa" ref={caixa} style={{ height: "min(62vh, 640px)" }}>
      <canvas ref={tela} aria-label={`Mapa da simulação: ${rotulo}`} role="img" />
      <div className="mapa-etiqueta">
        <Pastilha cor={cor} />
        {rotulo}
      </div>
      <div className="mapa-relogio">{formatarTempo(tempoS)}</div>
    </div>
  );
}
