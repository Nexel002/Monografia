import { configuracaoPorId } from "../../../shared/config/configuracoes";
import { Pastilha } from "../../../shared/ui/Pastilha";
import { formatarDecimal, formatarInteiro, formatarVariacao } from "../../../shared/utils/formatar";
import type { LinhaDaComparacao } from "../types/resultados";
import { variacaoFaceAoFixo } from "../utils/variacao";

/** A tabela é também a «vista em tabela» dos gráficos: nenhum valor depende só da cor. */
export function TabelaComparativa({ linhas }: { linhas: LinhaDaComparacao[] }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Configuração</th>
          <th>Espera média (s)</th>
          <th>Variação vs fixo</th>
          <th>Fila média (veíc.)</th>
          <th>Velocidade (km/h)</th>
          <th>Teleportes</th>
          <th>Sementes</th>
        </tr>
      </thead>
      <tbody>
        {linhas.map((l) => {
          const config = configuracaoPorId(l.configuracao);
          const variacao = variacaoFaceAoFixo(linhas, l.configuracao);
          return (
            <tr key={l.configuracao}>
              <td>
                <span className="com-pastilha">
                  <Pastilha cor={config.cor} />
                  {config.rotulo}
                </span>
              </td>
              <td>
                {formatarDecimal(l.espera_media_s)}
                {l.espera_desvio_s !== null && <small style={{ color: "var(--tinta-3)" }}> ± {formatarDecimal(l.espera_desvio_s)}</small>}
              </td>
              <td className={variacao === null ? "" : variacao <= 0 ? "melhor" : "pior"}>{variacao === null ? "—" : formatarVariacao(variacao)}</td>
              <td>{formatarDecimal(l.fila_media_veiculos)}</td>
              <td>{formatarDecimal(l.velocidade_media_ms * 3.6, 0)}</td>
              <td>{formatarInteiro(l.teleportes)}</td>
              <td>{l.sementes}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
