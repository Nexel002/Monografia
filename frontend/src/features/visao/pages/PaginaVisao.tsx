import { useState } from "react";
import { Cartao } from "../../../shared/ui/Cartao";
import { EstadoDaConsulta } from "../../../shared/ui/EstadoDaConsulta";
import { formatarDecimal, formatarInteiro } from "../../../shared/utils/formatar";
import { enderecoDoVideo } from "../api/visaoApi";
import { GraficoDeFila, GraficoDeFluxo } from "../components/GraficosDeContagem";
import { VisaoAoVivo } from "../components/VisaoAoVivo";
import { usePastas, useResumoDeVisao } from "../hooks/useVisao";
import { ROTULO_DO_TIPO, TIPOS_DE_VEICULO } from "../types/visao";

type Separador = "ao-vivo" | "completa";

/** O processamento de todos os fotogramas: a contagem de referência, já calculada. */
function ContagemCompleta() {
  const pastas = usePastas();
  const [escolhida, setEscolhida] = useState<string | null>(null);
  const comVideo = (pastas.data ?? []).filter((p) => p.tem_video);
  const pasta = escolhida && comVideo.some((p) => p.pasta === escolhida) ? escolhida : (comVideo[0]?.pasta ?? null);
  const resumo = useResumoDeVisao(pasta);

  return (
    <>
      <EstadoDaConsulta consulta={pastas} vazio={() => comVideo.length === 0} mensagemVazia="Ainda não há vídeos processados. Corre python -m gestao_trafego.visao.contar --video ..." alturaDoEsqueleto={380}>
        {() => (
          <div className="grelha grelha-2" style={{ gridTemplateColumns: "minmax(0, 1.5fr) minmax(0, 1fr)" }}>
            <Cartao
              titulo="Vídeo anotado"
              accao={
                <label className="campo" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                  Processamento
                  <select value={pasta ?? ""} onChange={(e) => setEscolhida(e.target.value)} disabled={comVideo.length === 0}>
                    {comVideo.map((p) => (
                      <option key={p.pasta} value={p.pasta}>
                        {p.pasta.replace("visao_", "")} {p.tamanho_imagem ? `· imagem ${p.tamanho_imagem}` : ""}
                      </option>
                    ))}
                  </select>
                </label>
              }
            >
              {pasta && <video className="video" src={enderecoDoVideo(pasta)} controls preload="metadata" />}
              <p className="nota">
                Resultado de analisar todos os fotogramas do vídeo (a referência). Em CPU o processamento é mais lento do que o vídeo; por
                isso o modo «Ao vivo» vê só uma parte dos fotogramas e pode contar menos.
              </p>
            </Cartao>
            <Cartao titulo="Contagem">
              <EstadoDaConsulta consulta={resumo} alturaDoEsqueleto={260}>
                {(r) => (
                  <>
                    <div className="indicadores">
                      <div className="indicador">
                        <span>Veículos contados</span>
                        <strong>{formatarInteiro(r.total)}</strong>
                        <small>{r.duracao_processada_s ? `em ${formatarInteiro(r.duracao_processada_s)} s de vídeo` : " "}</small>
                      </div>
                      {TIPOS_DE_VEICULO.map((t) => (
                        <div className="indicador" key={t}>
                          <span>{ROTULO_DO_TIPO[t]}</span>
                          <strong>{formatarInteiro(r.por_tipo[t] ?? 0)}</strong>
                        </div>
                      ))}
                    </div>
                    <p className="nota">
                      Modelo {r.modelo}
                      {r.tamanho_imagem ? `, imagem ${r.tamanho_imagem}` : ""}
                      {r.fps_de_processamento ? `, ${formatarDecimal(r.fps_de_processamento)} fotogramas/s em CPU` : ""}. A precisão ainda não está medida: falta uma contagem manual.
                    </p>
                  </>
                )}
              </EstadoDaConsulta>
            </Cartao>
          </div>
        )}
      </EstadoDaConsulta>

      {pasta && (
        <EstadoDaConsulta consulta={resumo} alturaDoEsqueleto={120}>
          {(r) =>
            r.janelas && r.janelas.length > 0 ? (
              <div className="grelha grelha-2">
                <Cartao titulo="Veículos contados por janela de 10 s">
                  <GraficoDeFluxo janelas={r.janelas} />
                </Cartao>
                <Cartao titulo="Fila estimada (veículos parados a montante da linha)">
                  <GraficoDeFila janelas={r.janelas} />
                </Cartao>
              </div>
            ) : (
              <div className="estado-mensagem">Este processamento é anterior à contagem por janelas. Volta a correr a visão para ver os gráficos.</div>
            )
          }
        </EstadoDaConsulta>
      )}
    </>
  );
}

export function PaginaVisao() {
  const [separador, setSeparador] = useState<Separador>("ao-vivo");
  return (
    <>
      <div className="titulo-de-pagina">
        <div>
          <h1>Visão computacional</h1>
          <p>
            Uma câmara conta os veículos que cruzam a linha branca. O detector (YOLO) reconhece o tipo de cada veículo e segue-o; a contagem
            usa a base da caixa. Verde = já contado, amarelo = ainda por contar.
          </p>
        </div>
        <div className="segmentado" role="group" aria-label="Modo">
          <button aria-pressed={separador === "ao-vivo"} onClick={() => setSeparador("ao-vivo")}>
            Ao vivo
          </button>
          <button aria-pressed={separador === "completa"} onClick={() => setSeparador("completa")}>
            Contagem completa
          </button>
        </div>
      </div>
      {separador === "ao-vivo" ? <VisaoAoVivo /> : <ContagemCompleta />}
    </>
  );
}
