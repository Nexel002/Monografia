// Os três cenários em que as cinco configurações foram comparadas. `escala` multiplica a procura (0,5 = metade do tráfego).
export type IdDoCenario = "ponta-via" | "ponta" | "normal";

export interface Cenario {
  id: IdDoCenario;
  rotulo: string;
  incidente: boolean;
  escala: number;
  descricao: string;
}

export const CENARIOS: Cenario[] = [
  { id: "ponta-via", rotulo: "Hora de ponta + via cortada", incidente: true, escala: 1, descricao: "Tráfego de hora de ponta e, aos 20 minutos, a Av. 24 de Julho fica cortada durante 10 minutos." },
  { id: "ponta", rotulo: "Hora de ponta", incidente: false, escala: 1, descricao: "Tráfego de hora de ponta, sem incidentes." },
  { id: "normal", rotulo: "Hora normal", incidente: false, escala: 0.5, descricao: "Metade do tráfego da hora de ponta, sem incidentes." },
];

export const cenarioPorId = (id: IdDoCenario): Cenario => CENARIOS.find((c) => c.id === id) ?? CENARIOS[0];
