import { Activity, Bot, Camera, LineChart, Moon, Network, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";

type Tema = "dark" | "light";

function temaInicial(): Tema {
  // O armazenamento pode falhar (janela privada, dados bloqueados): a página tem de funcionar sem ele.
  try {
    const guardado = localStorage.getItem("tema");
    if (guardado === "light" || guardado === "dark") return guardado;
  } catch {
    /* sem armazenamento: usa o tema escuro por omissão */
  }
  return "dark";
}

const LIGACOES = [
  { para: "/", rotulo: "Simulação ao vivo", icone: Network, fim: true },
  { para: "/resultados", rotulo: "Resultados", icone: Activity },
  { para: "/previsao", rotulo: "Previsão", icone: LineChart },
  { para: "/visao", rotulo: "Visão computacional", icone: Camera },
  { para: "/assistente", rotulo: "Assistente", icone: Bot },
];

export function Cabecalho() {
  const [tema, setTema] = useState<Tema>(temaInicial);

  useEffect(() => {
    document.documentElement.dataset.theme = tema;
    try {
      localStorage.setItem("tema", tema);
    } catch {
      /* ver acima */
    }
  }, [tema]);

  return (
    <header className="cabecalho">
      <div className="marca">
        <Network size={20} aria-hidden />
        <span>
          Tráfego Maputo <small>· semáforos com IA</small>
        </span>
      </div>
      <nav className="navegacao" aria-label="Secções">
        {LIGACOES.map(({ para, rotulo, icone: Icone, fim }) => (
          <NavLink key={para} to={para} end={fim} className={({ isActive }) => (isActive ? "activa" : "")}>
            <Icone size={16} aria-hidden />
            {rotulo}
          </NavLink>
        ))}
      </nav>
      <button onClick={() => setTema(tema === "dark" ? "light" : "dark")} aria-label={tema === "dark" ? "Mudar para o tema claro" : "Mudar para o tema escuro"}>
        {tema === "dark" ? <Sun size={16} /> : <Moon size={16} />}
      </button>
    </header>
  );
}
