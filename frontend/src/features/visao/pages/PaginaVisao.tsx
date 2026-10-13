import { useState } from "react";
import { Cartao } from "../../../shared/ui/Cartao";
import { EstadoDaConsulta } from "../../../shared/ui/EstadoDaConsulta";
import { formatarDecimal, formatarInteiro } from "../../../shared/utils/formatar";
import { enderecoDoVideo } from "../api/visaoApi";
import { GraficoDeFila, GraficoDeFluxo } from "../components/GraficosDeContagem";
import { usePastas, useResumoDeVisao } from "../hooks/useVisao";
import { ROTULO_DO_TIPO, TIPOS_DE_VEICULO } from "../types/visao";

export function PaginaVisao() {
  const pastas = usePastas();
  const [escolhida, setEscolhida] = useState<string | null>(null);
  const comVideo = (pastas.data ?? []).filter((p) => p.tem_video);
  const pasta = escolhida && comVideo.some((p) => p.pasta === escolhida) ? escolhida : (comVideo[0]?.pasta ?? null);
  const resumo = useResumoDeVisao(pasta);

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
        <label className="campo">
          Processamento
          <select value={pasta ?? ""} onChange={(e) => setEscolhida(e.target.value)} disabled={comVideo.length === 0}>
            {comVideo.map((p) => (
              <option key={p.pasta} value={p.pasta}>
                {p.pasta.replace("visao_", "")} {p.tamanho_imagem ? `· imagem ${p.tamanho_imagem}` : ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      <EstadoDaConsulta consulta={pastas} vazio={() => comVideo.length === 0} mensagemVazia="Ainda não há vídeos processados. Corre python -m gestao_trafego.visao.contar --video ..." alturaDoEsqueleto={380}>
        {() => (
          <div className="grelha grelha-2" style={{ gridTemplateColumns: "minmax(0, 1.5fr) minmax(0, 1fr)" }}>
            <Cartao titulo="Vídeo anotado">
              {pasta && <video className="video" src={enderecoDoVideo(pasta)} controls preload="metadata" />}
              <p className="nota">
                O vídeo é de uma autoestrada (Pexels), não de um cruzamento de Maputo. A contagem oficial vem do processamento de todos os
                fotogramas; em CPU, a análise ao vivo vê só uma parte e subconta.
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
