import { BellOff, History } from "lucide-react";
import type { Esquemas } from "@/api/cliente";
import { EstadoErro } from "@/componentes/EstadoErro";
import { EstadoVazio } from "@/componentes/EstadoVazio";
import { TabelaRolavel } from "@/componentes/TabelaRolavel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SeloRegra } from "@/regras/SeloRegra";
import { EsqueletoTabela } from "@/visao-geral/Esqueletos";
import { LIMITE_ALERTAS } from "./filtros";
import {
  AVISO_REGRA_MUDOU,
  celulasAlerta,
  estadoVazioAlertas,
  type FaseAlertas,
  regraDoAlerta,
  TEXTO_FILTROS_INVALIDOS,
  textoContagem,
} from "./tabela";

interface Props {
  fase: FaseAlertas;
  comFiltro: boolean;
  /** Regras atuais (GET /regras): só decidem o aviso "a regra mudou". */
  regras: readonly Esquemas["RegraSaida"][] | undefined;
  aoTentarNovamente: () => void;
  tentando: boolean;
}

/**
 * Resultado de GET /alertas, conforme a fase (faseAlertas). O status da tela fica no
 * ConteudoAlertas: o esqueleto aqui é só visual. O que disparou vem da cópia gravada no
 * alerta; a regra atual só decide o aviso. Com LIMITE_ALERTAS itens, a descrição do
 * cartão vira o aviso de limite (textoContagem).
 */
export function TabelaAlertas({ fase, comFiltro, regras, aoTentarNovamente, tentando }: Props) {
  switch (fase.fase) {
    case "invalida":
      return <p className="text-sm text-muted-foreground">{TEXTO_FILTROS_INVALIDOS}</p>;
    case "aguardando":
    case "carregando":
      return <EsqueletoTabela linhas={6} comStatus={false} />;
    case "erro":
      return <EstadoErro erro={fase.erro} aoTentarNovamente={aoTentarNovamente} tentando={tentando} />;
    case "pronta":
      break;
  }

  if (fase.alertas.length === 0) {
    const vazio = estadoVazioAlertas(comFiltro);
    return <EstadoVazio Icone={BellOff} titulo={vazio.titulo} texto={vazio.texto} acao={vazio.acao} />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2>Alertas</h2>
        </CardTitle>
        <CardDescription>{textoContagem(fase.alertas.length, LIMITE_ALERTAS)}</CardDescription>
      </CardHeader>
      <CardContent>
        <TabelaRolavel legenda="Alertas gerados pelo motor de regras, do dia mais recente para o mais antigo">
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Dia</TableHead>
              <TableHead scope="col">Campanha</TableHead>
              <TableHead scope="col">Regra</TableHead>
              <TableHead scope="col">O que disparou</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {fase.alertas.map((alerta) => {
              const c = celulasAlerta(alerta, regraDoAlerta(regras, alerta));
              return (
                <TableRow key={c.id} className="align-top">
                  <TableHead scope="row" className="font-medium whitespace-nowrap tabular-nums">
                    {c.dia}
                  </TableHead>
                  <TableCell>{c.campanha}</TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      <SeloRegra codigo={c.codigo} />
                      <span className="text-muted-foreground">{c.nome}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <ul className="flex flex-col gap-1">
                      {c.disparos.map((d, i) => (
                        <li key={i} className="tabular-nums">
                          <span aria-hidden>{d.visivel}</span>
                          <span className="sr-only">{d.acessivel}</span>
                        </li>
                      ))}
                    </ul>
                    {c.regraMudou === true && (
                      <p className="mt-1.5 flex items-start gap-1.5 text-xs text-muted-foreground">
                        <History aria-hidden className="mt-0.5 size-3.5 shrink-0" />
                        {AVISO_REGRA_MUDOU}
                      </p>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </TabelaRolavel>
      </CardContent>
    </Card>
  );
}
