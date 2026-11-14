// Contraste WCAG 2.x para cores OKLCH. Só os testes importam este módulo
// (não entra no bundle). Conversão OKLCH -> sRGB conforme Björn Ottosson,
// "A perceptual color space for image processing" (2020).

export interface Oklch {
  l: number;
  c: number;
  h: number;
}

/** sRGB codificado (0 a 1, com gama), já recortado para a gama. */
export type Rgb = readonly [number, number, number];

const OKLCH = /^oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)$/;

export function lerOklch(texto: string): Oklch {
  const m = OKLCH.exec(texto.trim());
  if (!m) throw new Error(`cor fora do formato oklch(L C H): ${texto}`);
  return { l: Number(m[1]), c: Number(m[2]), h: Number(m[3]) };
}

function oklchParaLinear({ l, c, h }: Oklch): [number, number, number] {
  const rad = (h * Math.PI) / 180;
  const a = c * Math.cos(rad);
  const b = c * Math.sin(rad);
  const l_ = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m_ = (l - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s_ = (l - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [
    4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
    -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
    -0.0041960863 * l_ - 0.7034186147 * m_ + 1.707614701 * s_,
  ];
}

const TOLERANCIA_GAMA = 0.001;

/** A cor cabe no sRGB? Fora dele, o navegador ajusta e o contraste calculado deixa de valer. */
export function dentroDaGama(cor: Oklch): boolean {
  return oklchParaLinear(cor).every((v) => v >= -TOLERANCIA_GAMA && v <= 1 + TOLERANCIA_GAMA);
}

const codificar = (v: number) => (v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055);
const decodificar = (v: number) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
const recortar = (v: number) => Math.min(1, Math.max(0, v));

export function oklchParaRgb(cor: Oklch): Rgb {
  const [r, g, b] = oklchParaLinear(cor).map((v) => codificar(recortar(v)));
  return [r!, g!, b!];
}

/** Cor com transparência sobre um fundo opaco (composição no sRGB codificado, como o navegador). */
export function compor(frente: Rgb, alfa: number, fundo: Rgb): Rgb {
  return [0, 1, 2].map((i) => frente[i]! * alfa + fundo[i]! * (1 - alfa)) as unknown as Rgb;
}

/**
 * Distância entre duas cores no OKLab, ×100 (a escala do validador de paleta da skill
 * dataviz: abaixo de 15, as séries de um gráfico ficam difíceis de separar mesmo com
 * visão normal). OKLCH → OKLab é só polar → cartesiano: a = C·cos h, b = C·sin h.
 */
export function deltaEOk(p: Oklch, q: Oklch): number {
  const lab = ({ l, c, h }: Oklch) => [l, c * Math.cos((h * Math.PI) / 180), c * Math.sin((h * Math.PI) / 180)];
  const [a, b] = [lab(p), lab(q)];
  return 100 * Math.hypot(a[0]! - b[0]!, a[1]! - b[1]!, a[2]! - b[2]!);
}

export function luminancia(rgb: Rgb): number {
  const [r, g, b] = rgb.map(decodificar);
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
}

export function razaoContraste(a: Rgb, b: Rgb): number {
  const [la, lb] = [luminancia(a), luminancia(b)];
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

/**
 * Lê as variáveis `--nome: valor;` de um bloco do CSS (ex.: ":root", ".dark").
 * Aceita só o primeiro bloco com esse seletor exato no início da linha.
 */
export function lerBloco(css: string, seletor: string): Record<string, string> {
  const inicio = css.search(new RegExp(`^${seletor.replace(".", "\\.")}\\s*\\{`, "m"));
  if (inicio < 0) throw new Error(`bloco ${seletor} não encontrado`);
  const fim = css.indexOf("}", inicio);
  const corpo = css.slice(css.indexOf("{", inicio) + 1, fim).replace(/\/\*[\s\S]*?\*\//g, "");
  const tokens: Record<string, string> = {};
  for (const m of corpo.matchAll(/--([\w-]+)\s*:\s*([^;]+);/g)) tokens[m[1]!] = m[2]!.trim();
  return tokens;
}

/** Valor final de um token, seguindo `var(--outro)` (o tema escuro herda do :root o que não redefine). */
export function resolver(nome: string, ...camadas: Record<string, string>[]): string {
  const vistos = new Set<string>();
  let atual = nome;
  for (;;) {
    if (vistos.has(atual)) throw new Error(`referência circular em --${nome}`);
    vistos.add(atual);
    const valor = camadas.map((c) => c[atual]).find((v) => v !== undefined);
    if (valor === undefined) throw new Error(`token --${atual} não definido`);
    const ref = /^var\(--([\w-]+)\)$/.exec(valor);
    if (!ref) return valor;
    atual = ref[1]!;
  }
}
