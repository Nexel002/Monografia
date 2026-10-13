import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Cabecalho } from "./app/layout/Cabecalho";
import { PaginaAssistente } from "./features/assistente/pages/PaginaAssistente";
import { PaginaPrevisao } from "./features/previsao/pages/PaginaPrevisao";
import { PaginaResultados } from "./features/resultados/pages/PaginaResultados";
import { PaginaSimulacao } from "./features/simulacao/pages/PaginaSimulacao";
import { PaginaVisao } from "./features/visao/pages/PaginaVisao";

// Os resultados guardados só mudam quando se importa de novo: não vale a pena voltar a pedi-los a cada foco da janela.
const cliente = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1, staleTime: 60_000 } } });

export default function App() {
  return (
    <QueryClientProvider client={cliente}>
      <BrowserRouter>
        <div className="aplicacao">
          <Cabecalho />
          <main className="conteudo">
            <Routes>
              <Route path="/" element={<PaginaSimulacao />} />
              <Route path="/resultados" element={<PaginaResultados />} />
              <Route path="/previsao" element={<PaginaPrevisao />} />
              <Route path="/visao" element={<PaginaVisao />} />
              <Route path="/assistente" element={<PaginaAssistente />} />
              <Route path="*" element={<div className="estado-mensagem">Esta página não existe.</div>} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
