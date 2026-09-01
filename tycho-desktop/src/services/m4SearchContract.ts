/**
 * Contrato compartilhado da busca evidencial do Marco 4.
 *
 * A interface usa este módulo para validar o payload antes do IPC. A ponte
 * Tauri/Rust aplica novamente as mesmas restrições, resolve o SQLite M3
 * previamente provisionado e executa o sidecar dedicado. Nunca passe um
 * caminho de banco vindo da interface para essa função.
 */

export const M4_SEARCH_CONTRACT_VERSION = "m4-evidential-v1" as const;
export const DEFAULT_M4_SEARCH_LIMIT = 50;
export const MAX_M4_SEARCH_LIMIT = 500;
export const MAX_M4_FILTER_LENGTH = 512;

export const M4_ENTITY_TYPES = [
  "EXCLUSAO",
  "NUCLEO_LEXICAL",
  "NUCLEO_FUNCIONAL",
  "NUCLEO_FRONTEIRA",
  "EVIDENCIA_AUXILIAR",
  "PROJECAO_FONTE",
  "EVIDENCIA_CARTOGRAFICA",
] as const;

export type M4EntityType = (typeof M4_ENTITY_TYPES)[number];

export interface M4SearchCriteria {
  entityType?: M4EntityType;
  analyticalLabel?: string;
  projection?: string;
  token?: string;
  ruleId?: string;
  limit?: number;
}

export interface M4SearchCommand {
  command: "search";
  args: string[];
}

export class M4SearchCriteriaError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "M4SearchCriteriaError";
  }
}

type FilterName = Exclude<keyof M4SearchCriteria, "limit">;

const FILTER_FLAGS: Readonly<Record<FilterName, string>> = {
  entityType: "--entity-type",
  analyticalLabel: "--label",
  projection: "--projection",
  token: "--token",
  ruleId: "--rule",
};

function normaliseFilter(name: FilterName, value: string | undefined): string | undefined {
  if (value === undefined) {
    return undefined;
  }

  const normalised = value.trim();
  if (!normalised) {
    return undefined;
  }
  if (normalised.length > MAX_M4_FILTER_LENGTH) {
    throw new M4SearchCriteriaError(
      `O filtro ${name} excede ${MAX_M4_FILTER_LENGTH} caracteres.`,
    );
  }
  if (normalised.includes("\u0000")) {
    throw new M4SearchCriteriaError(`O filtro ${name} contém um caractere inválido.`);
  }
  if (normalised.startsWith("-")) {
    throw new M4SearchCriteriaError(`O filtro ${name} não pode começar com hífen.`);
  }
  if (
    name === "entityType" &&
    !M4_ENTITY_TYPES.includes(normalised as M4EntityType)
  ) {
    throw new M4SearchCriteriaError("O tipo de entidade informado não pertence ao contrato Marco 4.");
  }
  return normalised;
}

function normaliseLimit(value: number | undefined): number {
  if (value === undefined) {
    return DEFAULT_M4_SEARCH_LIMIT;
  }
  if (!Number.isInteger(value) || value < 1 || value > MAX_M4_SEARCH_LIMIT) {
    throw new M4SearchCriteriaError(
      `O limite deve ser um inteiro entre 1 e ${MAX_M4_SEARCH_LIMIT}.`,
    );
  }
  return value;
}

/**
 * Gera apenas argumentos posicionais para `busca_rastreavel.py search`.
 *
 * O processo Rust deve acrescentar `--db <caminho-confiável>` depois de
 * verificar a disponibilidade e a proveniência do artefato. Como a execução
 * recebe um vetor de argumentos, nenhum filtro é concatenado em uma shell.
 */
export function buildM4SearchCommand(criteria: M4SearchCriteria): M4SearchCommand {
  const filters = (Object.keys(FILTER_FLAGS) as FilterName[])
    .map((name) => [name, normaliseFilter(name, criteria[name])] as const)
    .filter((entry): entry is readonly [FilterName, string] => entry[1] !== undefined);

  if (filters.length === 0) {
    throw new M4SearchCriteriaError(
      "Informe ao menos um filtro evidencial antes de consultar o Marco 4.",
    );
  }

  const args = ["search"];
  for (const [name, value] of filters) {
    args.push(FILTER_FLAGS[name], value);
  }
  args.push("--limit", String(normaliseLimit(criteria.limit)));

  return { command: "search", args };
}

export type M4EvidenceType =
  | "ROTULO_PSD"
  | "TOKEN"
  | "RELACAO_ORIGEM"
  | "ORDEM_IRMAO"
  | "LEXICO_CONGELADO";

/** O JSON que a ponte Tauri/Rust decodifica do sidecar M4. */
export interface M4AnalysisIdentity {
  analysis_id: number;
  schema_version: string;
  engine_version: string;
  engine_sha256: string;
  ruleset_version: string;
  ruleset_sha256: string;
  source_database_sha256: string;
}

export interface M4Origin {
  relative_path: string;
  document_id: number;
  block_id: number;
  candidate_ordinal: number;
  block_ordinal: number;
  block_sha256: string;
  import_result: "IMPORTADO";
  analysis_scope_status: "ANALISADA";
  sentence_id: number;
  external_id: string | null;
  root_label: string;
  structure_class: string;
  tree_sha256: string;
  leaves_sha256: string;
}

export interface M4Anchor {
  node_id: number;
  source_label: string;
  source_base: string;
  source_function: string | null;
  preorder: number;
  leaf_ordinal: number | null;
  token: string | null;
}

export interface M4Entity {
  entity_id: number;
  type: M4EntityType;
  analytical_label: string;
  source_projection: string | null;
  evidenced_projection: string | null;
  order: number;
  details: unknown;
}

export interface M4Decision {
  decision_id: number;
  rule_id: string;
  confidence: number;
  confidence_method: "HEURISTICA";
  evidence_status: string;
  review_status: "PENDENTE";
  justification: string;
}

export interface M4Evidence {
  evidence_id: number;
  type: M4EvidenceType;
  ordinal: number;
  value: unknown;
  sha256: string;
  description: string;
}

export interface M4SearchResult {
  analysis: M4AnalysisIdentity;
  origin: M4Origin;
  anchor: M4Anchor;
  entity: M4Entity;
  decision: M4Decision;
  evidence: M4Evidence[];
}

export interface M4SearchQuery {
  entity_type: M4EntityType | null;
  label: string | null;
  projection: string | null;
  token: string | null;
  rule: string | null;
  limit: number;
}

export interface M4SearchValidation {
  mode: "precondicao_m3_promovido" | "integral_m3_m2";
  full_source_validation: boolean;
}

export interface M4SearchSuccess {
  ok: true;
  analysis: M4AnalysisIdentity;
  query: M4SearchQuery;
  validation: M4SearchValidation;
  result_count: number;
  results: M4SearchResult[];
}

export interface M4SearchFailure {
  ok: false;
  code?: string;
  error: string;
}

export type M4SearchResponse = M4SearchSuccess | M4SearchFailure;

/**
 * Texto obrigatório de apresentação: o Marco 4 oferece classificação e
 * evidências rastreáveis; não confirma uma hipótese gramatical automaticamente.
 */
export function m4ReviewNotice(decision: M4Decision): string {
  if (decision.review_status === "PENDENTE") {
    return "Classificação heurística com evidências rastreáveis; pendente de revisão humana e sem confirmação científica automática.";
  }
  return "Classificação evidencial; consulte as evidências e a revisão associada antes de inferir uma conclusão científica.";
}
