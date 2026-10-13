// As cinco formas de controlar os semáforos que a monografia compara. O identificador é o mesmo que a
// API e a base de dados usam. A cor segue a configuração em TODOS os ecrãs (nunca a posição na lista).
export type IdDaConfiguracao = "fixo" | "local" | "local+vias" | "coordenado" | "coordenado+vias";

export interface Configuracao {
  id: IdDaConfiguracao;
  rotulo: string;
  curto: string;
  cor: string;
  descricao: string;
}

export const CONFIGURACOES: Configuracao[] = [
  { id: "fixo", rotulo: "Tempo fixo (como hoje)", curto: "Tempo fixo", cor: "var(--cfg-fixo)", descricao: "Ciclos fixos, como os semáforos de Maputo hoje." },
  { id: "local", rotulo: "Adaptativo local", curto: "Local", cor: "var(--cfg-local)", descricao: "Cada cruzamento decide sozinho por Max-Pressure." },
  { id: "local+vias", rotulo: "Local + vias alternativas", curto: "Local + vias", cor: "var(--cfg-local-vias)", descricao: "Adaptativo local e recomendação de rotas a 50 % dos condutores." },
  { id: "coordenado", rotulo: "Coordenado", curto: "Coordenado", cor: "var(--cfg-coordenado)", descricao: "Adaptativo local com um coordenador que evita bloqueios a montante." },
  { id: "coordenado+vias", rotulo: "Coordenado + vias alternativas", curto: "Coordenado + vias", cor: "var(--cfg-coordenado-vias)", descricao: "O sistema completo: coordenação e recomendação de rotas." },
];

export const configuracaoPorId = (id: string): Configuracao =>
  CONFIGURACOES.find((c) => c.id === id) ?? { id: id as IdDaConfiguracao, rotulo: id, curto: id, cor: "var(--tinta-3)", descricao: "" };
