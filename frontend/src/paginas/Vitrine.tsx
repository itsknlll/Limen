// PROVISÓRIA (Fase 1): mostra os tokens para aprovação do visual nos dois temas.
// Sai quando entrar o roteador, junto com o layout e as telas.
import { AlertTriangle, Plus, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { aparenciaDaRegra } from "@/regras/aparencia";
import { SeloRegra } from "@/regras/SeloRegra";
import { useTema } from "@/tema/contexto";
import { SeletorTema } from "@/tema/SeletorTema";

const NEUTROS = [
  ["background", "Fundo"],
  ["card", "Cartão"],
  ["muted", "Suave"],
  ["border", "Borda"],
  ["input", "Borda de campo"],
  ["muted-foreground", "Texto suave"],
  ["foreground", "Texto"],
] as const;

const DESTAQUE = [
  ["primary", "Índigo (destaque)"],
  ["ring", "Anel de foco"],
  ["destructive", "Erro"],
] as const;

const REGRAS = ["R1", "R2", "R3", "R4"] as const;

// O CardTitle do shadcn traz `group-data-[size=sm]/card:text-sm`. Essa variante tem
// especificidade maior que `.text-3xl` e o `cn` não a remove (é outra variante), então
// num <Card size="sm"> o número saía com 14 px. Repetir a variante com o tamanho certo
// faz o `cn` substituí-la (ver utils.test.ts).
const CLASSE_KPI = "text-3xl group-data-[size=sm]/card:text-3xl font-semibold tabular-nums";

const ESCALA = [
  ["text-3xl font-semibold tabular-nums", "30 px · 600 · KPI", "1.234"],
  ["text-2xl font-semibold tracking-tight", "24 px · 600 · título da página", "Visão geral"],
  ["text-lg font-semibold", "18 px · 600 · título de seção", "Alertas por dia"],
  ["text-sm", "14 px · 400 · corpo e tabelas", "Campanha A — 30 registros entre 13/10 e 11/11/2026"],
  ["text-sm font-medium", "14 px · 500 · rótulo", "Campanhas ativas"],
  ["text-xs text-muted-foreground", "12 px · legenda", "Atualizado em 13/11/2026 às 12:44"],
] as const;

function Amostra({ token, rotulo }: { token: string; rotulo: string }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="size-10 shrink-0 rounded-md ring-1 ring-foreground/10"
        style={{ background: `var(--${token})` }}
      />
      <div className="min-w-0">
        <p className="text-sm font-medium">{rotulo}</p>
        <p className="truncate font-mono text-xs text-muted-foreground">--{token}</p>
      </div>
    </div>
  );
}

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">{titulo}</h2>
      {children}
    </section>
  );
}

export function Vitrine() {
  const { preferencia, temaResolvido } = useTema();

  return (
    <div className="min-h-svh">
      <header className="sticky top-0 z-10 border-b bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between gap-4 px-4">
          <div className="flex items-baseline gap-3">
            <span className="text-base font-semibold tracking-tight">Limen</span>
            <span className="text-xs text-muted-foreground">vitrine provisória · Fase 1</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              preferência <strong className="font-medium text-foreground">{preferencia}</strong> → tema{" "}
              <strong className="font-medium text-foreground">{temaResolvido}</strong>
            </span>
            <SeletorTema />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-12 px-4 py-10">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Tokens, temas e selos</h1>
          <p className="text-sm text-muted-foreground">
            Cores em OKLCH, contraste conferido por teste (WCAG 2.x). Troque o tema no canto superior
            direito.
          </p>
        </div>

        <Secao titulo="Neutros e destaque">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[...NEUTROS, ...DESTAQUE].map(([token, rotulo]) => (
              <Amostra key={token} token={token} rotulo={rotulo} />
            ))}
          </div>
        </Secao>

        <Secao titulo="Regras">
          <p className="text-sm text-muted-foreground">
            Cor, ícone e código sempre juntos: a cor nunca é o único sinal. R4 representa uma regra criada
            pelo usuário (visual neutro).
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Sobre o cartão</CardTitle>
                <CardDescription>Selo curto e com nome</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  {REGRAS.map((c) => (
                    <SeloRegra key={c} codigo={c} />
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  {REGRAS.map((c) => (
                    <SeloRegra key={c} codigo={c} comNome nome={c === "R4" ? "Regra do usuário" : undefined} />
                  ))}
                </div>
              </CardContent>
            </Card>
            <div className="space-y-3 rounded-xl bg-background p-4 ring-1 ring-foreground/10">
              <p className="text-sm font-medium">Sobre o fundo da página — séries do gráfico</p>
              {REGRAS.map((c) => {
                const { Icone, corCss, classes, nomePadrao } = aparenciaDaRegra(c);
                return (
                  <div key={c} className="flex items-center gap-3">
                    <Icone aria-hidden className={`size-4 ${classes.texto}`} />
                    <span className="w-8 text-sm font-semibold">{c}</span>
                    <div className="h-3 flex-1 rounded-sm" style={{ background: corCss }} />
                    <span className="w-40 truncate text-xs text-muted-foreground">
                      {nomePadrao ?? "regra do usuário"}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </Secao>

        <Secao titulo="Tipografia — Inter (auto-hospedada)">
          <div className="divide-y rounded-xl bg-card ring-1 ring-foreground/10">
            {ESCALA.map(([classes, legenda, exemplo]) => (
              <div key={legenda} className="flex flex-col gap-1 p-4 sm:flex-row sm:items-baseline sm:gap-6">
                <span className="w-56 shrink-0 font-mono text-xs text-muted-foreground">{legenda}</span>
                <span className={classes}>{exemplo}</span>
              </div>
            ))}
          </div>
        </Secao>

        <Secao titulo="Componentes">
          <div className="flex flex-wrap items-center gap-2">
            <Button>
              <RefreshCw data-icon="inline-start" aria-hidden />
              Sincronizar campanhas
            </Button>
            <Button variant="outline">
              <Plus data-icon="inline-start" aria-hidden />
              Nova regra
            </Button>
            <Button variant="secondary">Secundário</Button>
            <Button variant="ghost">Fantasma</Button>
            <Button variant="destructive">Desativar regra</Button>
            <Button variant="link">Ver alertas</Button>
            <Button disabled>Desabilitado</Button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge>ENABLED</Badge>
            <Badge variant="secondary">PAUSED</Badge>
            <Badge variant="outline">sintética</Badge>
            <Badge variant="destructive">
              <AlertTriangle aria-hidden />
              Token revogado
            </Badge>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {[
              ["Alertas no período", "18", "13/10 a 11/11/2026"],
              ["Campanhas ativas", "2", "de 3 sincronizadas"],
              ["Registros avaliados", "60", "0 rejeitados"],
            ].map(([titulo, valor, detalhe]) => (
              <Card key={titulo} size="sm">
                <CardHeader>
                  <CardDescription>{titulo}</CardDescription>
                  <CardTitle className={CLASSE_KPI}>{valor}</CardTitle>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground">{detalhe}</CardContent>
              </Card>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Números de exemplo (iguais aos do IN-02b), só para ver a tipografia; nada aqui vem da API.
          </p>
        </Secao>
      </main>
    </div>
  );
}
