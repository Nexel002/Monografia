import { formatarDecimal, formatarInteiro } from "../../../shared/utils/formatar";
import type { IndicadoresMsg } from "../types/mensagens";

interface Props {
  indicadores: IndicadoresMsg | null;
  /** Indicadores do outro lado, para destacar quem está melhor. */
  outro: IndicadoresMsg | null;
}

type Melhor = "menos" | "mais";

/** «melhor» ou «pior» face ao outro lado; sem diferença relevante não se destaca nada (cor nunca sozinha: há o número). */
function classe(valor: number | undefined, outro: number | undefined, melhor: Melhor, margem: number): string {
  if (valor === undefined || outro === undefined || Math.abs(valor - outro) <= margem) return "";
  const esteMelhor = melhor === "menos" ? valor < outro : valor > outro;
  return esteMelhor ? "melhor" : "pior";
}

export function IndicadoresDoLado({ indicadores: k, outro }: Props) {
  return (
    <div className="indicadores">
      <div className="indicador">
        <span>Veículos na rede</span>
        <strong>{k ? formatarInteiro(k.na_rede) : "—"}</strong>
      </div>
      <div className="indicador">
        <span>Parados</span>
        <strong className={classe(k?.parados, outro?.parados, "menos", 2)}>{k ? formatarInteiro(k.parados) : "—"}</strong>
        <small>{k && k.na_rede ? `${formatarInteiro((100 * k.parados) / k.na_rede)} % da rede` : " "}</small>
      </div>
      <div className="indicador">
        <span>Velocidade média</span>
        <strong className={classe(k?.velocidade_media_ms, outro?.velocidade_media_ms, "mais", 0.2)}>
          {k ? formatarDecimal(k.velocidade_media_ms * 3.6, 0) : "—"}
          <small> km/h</small>
        </strong>
      </div>
      <div className="indicador">
        <span>Espera média</span>
        <strong className={classe(k?.espera_media_s, outro?.espera_media_s, "menos", 2)}>
          {k && k.chegados > 0 ? formatarDecimal(k.espera_media_s, 0) : "—"}
          <small> s</small>
        </strong>
        <small>dos {k ? formatarInteiro(k.chegados) : 0} que chegaram</small>
      </div>
    </div>
  );
}
