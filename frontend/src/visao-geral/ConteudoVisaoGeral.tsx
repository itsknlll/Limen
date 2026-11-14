import { CalendarX2, Megaphone, PlayCircle, type LucideIcon } from "lucide-react";
import { useResumo } from "@/api/consultas";
import { EstadoErro } from "@/componentes/EstadoErro";
import { EstadoVazio } from "@/componentes/EstadoVazio";
import { ROTAS } from "@/rotas";
import { AlertasPorRegra } from "./AlertasPorRegra";
import { CartoesKpi } from "./CartoesKpi";
import { estadoVazio, type EstadoVazio as TipoEstadoVazio } from "./dados";
import { EsqueletoResumo } from "./Esqueletos";
import { GraficoAlertasPorDia } from "./GraficoAlertasPorDia";
import { UltimasAvaliacoes } from "./UltimasAvaliacoes";

// Conteúdo da Visão geral, carregado sob demanda (React.lazy em paginas/VisaoGeral.tsx):
// o Recharts só é baixado quando a tela abre. O h1 fica fora, na página.

const VAZIOS: Record<Exclude<TipoEstadoVazio, "sem_alertas">, {
  Icone: LucideIcon;
  titulo: string;
  texto: string;
  acao: { rotulo: string; para: string };
}> = {
  sem_campanhas: {
    Icone: Megaphone,
    titulo: "Nenhuma campanha sincronizada",
    texto: "Sincronize as campanhas da conta do Google Ads para o motor ter o que avaliar.",
    acao: { rotulo: "Ir para Campanhas", para: ROTAS.campanhas },
  },
  sem_metricas: {
    Icone: CalendarX2,
    titulo: "Nenhuma métrica registrada",
    texto: "As campanhas ainda não têm métricas diárias. Sem elas, não há o que avaliar.",
    acao: { rotulo: "Ir para Campanhas", para: ROTAS.campanhas },
  },
  sem_avaliacoes: {
    Icone: PlayCircle,
    titulo: "O motor ainda não foi executado",
    texto: "Há campanhas e métricas. Execute uma avaliação para ver os alertas aqui.",
    acao: { rotulo: "Ir para Avaliações", para: ROTAS.avaliacoes },
  },
};

function SecaoResumo() {
  const consulta = useResumo();

  if (consulta.isPending) return <EsqueletoResumo />;
  if (consulta.isError) {
    return (
      <EstadoErro erro={consulta.error} aoTentarNovamente={() => void consulta.refetch()} tentando={consulta.isFetching} />
    );
  }

  const resumo = consulta.data;
  const vazio = estadoVazio(resumo);
  return (
    <div className="flex flex-col gap-6">
      <CartoesKpi resumo={resumo} />
      {/* sem_alertas não é vazio: a avaliação rodou e nada disparou; o gráfico mostra os zeros. */}
      {vazio && vazio !== "sem_alertas" ? (
        <EstadoVazio {...VAZIOS[vazio]} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <GraficoAlertasPorDia resumo={resumo} className="min-w-0 lg:col-span-2" />
          {/* self-start: sem ele, o item da grade estica até a altura do gráfico. */}
          <AlertasPorRegra resumo={resumo} className="self-start" />
        </div>
      )}
    </div>
  );
}

export default function ConteudoVisaoGeral() {
  return (
    <div className="flex flex-col gap-6">
      <SecaoResumo />
      <UltimasAvaliacoes />
    </div>
  );
}
