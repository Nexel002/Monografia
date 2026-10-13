import { FileText, Volume2 } from "lucide-react";
import { Cartao } from "../../../shared/ui/Cartao";
import { EstadoDaConsulta } from "../../../shared/ui/EstadoDaConsulta";
import { mensagemDeErro } from "../../../shared/utils/mensagemDeErro";
import { ConversaDoAssistente } from "../components/ConversaDoAssistente";
import { useEstadoDoAssistente, useRelatorio } from "../hooks/useAssistente";
import { falar } from "../utils/voz";

export function PaginaAssistente() {
  const estado = useEstadoDoAssistente();
  const relatorio = useRelatorio();

  return (
    <>
      <div className="titulo-de-pagina">
        <div>
          <h1>Assistente</h1>
          <p>
            Faz perguntas sobre os resultados, por escrito ou por voz. O assistente só consulta os números das simulações, da previsão e
            dos vídeos; não controla semáforos nem corre simulações, e diz quando um dado não existe ou é assumido.
          </p>
        </div>
      </div>

      <div className="grelha grelha-2" style={{ gridTemplateColumns: "minmax(0, 1.6fr) minmax(0, 1fr)" }}>
        <Cartao titulo="Conversa">
          <EstadoDaConsulta consulta={estado} alturaDoEsqueleto={420}>
            {(e) => <ConversaDoAssistente perguntasSugeridas={e.perguntas_sugeridas} />}
          </EstadoDaConsulta>
        </Cartao>

        <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>
          <Cartao titulo="Estado">
            <EstadoDaConsulta consulta={estado} alturaDoEsqueleto={90}>
              {(e) => (
                <ul className="lista-de-estado">
                  <li>
                    <span className={`ponto ${e.gemini_configurado ? "bom" : "aviso"}`} />
                    {e.gemini_configurado ? "Modelo de linguagem (Gemini) configurado" : "Sem Gemini: respostas em modo de segurança"}
                  </li>
                  <li>
                    <span className={`ponto ${e.voz_do_servidor ? "bom" : "aviso"}`} />
                    {e.voz_do_servidor ? "Voz de servidor disponível" : "Sem voz de servidor: usa a voz do browser"}
                  </li>
                </ul>
              )}
            </EstadoDaConsulta>
            <p className="nota">Dados enviados ao Gemini: apenas resultados agregados das simulações. A chave fica no servidor.</p>
          </Cartao>

          <Cartao
            titulo="Relatório automático"
            accao={
              <button className="primario" onClick={() => relatorio.mutate()} disabled={relatorio.isPending}>
                <FileText size={16} /> {relatorio.isPending ? "A gerar…" : "Gerar relatório"}
              </button>
            }
          >
            {relatorio.isPending && <div className="esqueleto" style={{ height: 120 }} role="status" aria-label="A gerar o relatório" />}
            {relatorio.isError && (
              <div className="estado-mensagem erro" role="alert">
                <div>
                  <strong>Não foi possível gerar o relatório</strong>
                  {mensagemDeErro(relatorio.error)}
                </div>
              </div>
            )}
            {relatorio.data && (
              <>
                <div className="relatorio-texto">{relatorio.data.texto}</div>
                <div className="balao-meta" style={{ marginTop: 8 }}>
                  <span className={`etiqueta ${relatorio.data.modo}`}>{relatorio.data.modo === "gemini" ? "Gemini" : "Modo de segurança"}</span>
                  <button className="icone" onClick={() => void falar(relatorio.data.texto)} aria-label="Ouvir o relatório" title="Ouvir o relatório">
                    <Volume2 size={14} />
                  </button>
                </div>
                {relatorio.data.aviso && <div className="balao-aviso">{relatorio.data.aviso}</div>}
              </>
            )}
            {!relatorio.isPending && !relatorio.isError && !relatorio.data && (
              <p className="nota">Gera um resumo curto da comparação das configurações, da previsão e da visão, com o que não está provado.</p>
            )}
          </Cartao>
        </div>
      </div>
    </>
  );
}
