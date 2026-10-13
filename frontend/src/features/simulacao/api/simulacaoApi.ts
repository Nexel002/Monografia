import { obter } from "../../../shared/api/cliente";
import type { Rede } from "../types/mensagens";

export const obterRede = () => obter<Rede>("/api/rede");
