// O CardTitle do shadcn traz `group-data-[size=sm]/card:text-sm`, de especificidade
// maior que `.text-3xl`; repetir a variante com o tamanho certo faz o `cn` trocá-la
// (decisão "KPI com 14 px" da Fase 1, testada em lib/utils.test.ts).
// Fica fora de CartoesKpi.tsx para o arquivo do componente exportar só componentes
// (regra react-refresh/only-export-components).
export const CLASSE_NUMERO =
  "text-3xl group-data-[size=sm]/card:text-3xl font-semibold tabular-nums";
