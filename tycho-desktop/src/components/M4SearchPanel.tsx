import { FormEvent, useState } from 'react';
import { AlertCircle, CheckCircle2, Database, FileText, Search, ShieldCheck } from 'lucide-react';
import {
  buildM4SearchCommand,
  m4ReviewNotice,
  searchM4,
  M4_ENTITY_TYPES,
  type M4EntityType,
  type M4SearchCriteria,
  type M4SearchResponse,
} from '../services/api';

const optional = (value: string): string | undefined => {
  const normalized = value.trim();
  return normalized || undefined;
};

export function M4SearchPanel() {
  const [entityType, setEntityType] = useState<M4EntityType | ''>('');
  const [analyticalLabel, setAnalyticalLabel] = useState('');
  const [projection, setProjection] = useState('');
  const [token, setToken] = useState('');
  const [ruleId, setRuleId] = useState('');
  const [limit, setLimit] = useState(50);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<M4SearchResponse | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const criteria: M4SearchCriteria = {
      entityType: entityType || undefined,
      analyticalLabel: optional(analyticalLabel),
      projection: optional(projection),
      token: optional(token),
      ruleId: optional(ruleId),
      limit,
    };

    try {
      // A mesma validação de allowlist usada pela ponte Rust é aplicada antes
      // do IPC. O resultado não fornece caminho de banco à interface.
      buildM4SearchCommand(criteria);
    } catch (error) {
      setResponse({
        ok: false,
        code: 'M4_INVALID_CRITERIA',
        error: error instanceof Error ? error.message : 'Critérios M4 inválidos.',
      });
      return;
    }

    setLoading(true);
    setResponse(null);
    try {
      setResponse(await searchM4(criteria));
    } finally {
      setLoading(false);
    }
  };

  const success = response?.ok ? response : null;
  const failure = response && !response.ok ? response : null;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <section className="bg-white rounded-xl shadow-xs border border-slate-200 p-6 space-y-4">
        <div className="flex gap-3 items-start">
          <div className="p-2 bg-indigo-50 text-indigo-700 rounded-lg">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900">Busca evidencial rastreável — Marco 4</h3>
            <p className="text-sm text-slate-600 mt-1 leading-relaxed">
              Consulte entidades, rótulos, projeções, tokens e regras do artefato Marco 3 promovido. Cada ocorrência preserva origem, âncora, evidência e estado de revisão; a busca não cria nós cartográficos.
            </p>
          </div>
        </div>
        <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          Classificações com revisão <strong>PENDENTE</strong> são evidências heurísticas, não confirmação científica automática. O caminho do banco é resolvido somente pelo aplicativo; esta tela não aceita arquivos ou caminhos.
        </p>
      </section>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-xs border border-slate-200 p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          <label className="text-xs font-semibold text-slate-600 space-y-1 block">
            Tipo de entidade
            <select
              value={entityType}
              onChange={(event) => setEntityType(event.target.value as M4EntityType | '')}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white"
            >
              <option value="">Qualquer tipo (exige outro filtro)</option>
              {M4_ENTITY_TYPES.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-600 space-y-1 block">
            Rótulo analítico
            <input maxLength={512} value={analyticalLabel} onChange={(event) => setAnalyticalLabel(event.target.value)} placeholder="NUCLEO_LEXICAL_NOMINAL" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono" />
          </label>
          <label className="text-xs font-semibold text-slate-600 space-y-1 block">
            Projeção fonte/evidenciada
            <input maxLength={512} value={projection} onChange={(event) => setProjection(event.target.value)} placeholder="MoodP_evaluative" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono" />
          </label>
          <label className="text-xs font-semibold text-slate-600 space-y-1 block">
            Token de origem
            <input maxLength={512} value={token} onChange={(event) => setToken(event.target.value)} placeholder="felizmente" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono" />
          </label>
          <label className="text-xs font-semibold text-slate-600 space-y-1 block">
            Regra Marco 3
            <input maxLength={512} value={ruleId} onChange={(event) => setRuleId(event.target.value)} placeholder="E_ADV" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono" />
          </label>
          <label className="text-xs font-semibold text-slate-600 space-y-1 block">
            Limite (1–500)
            <input type="number" min={1} max={500} value={limit} onChange={(event) => setLimit(Number(event.target.value))} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono" />
          </label>
        </div>
        <div className="flex justify-end">
          <button type="submit" disabled={loading} className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-semibold text-sm rounded-lg transition-colors">
            <Search className="w-4 h-4" />
            {loading ? 'Consultando evidências…' : 'Consultar Marco 4'}
          </button>
        </div>
      </form>

      {failure && (
        <section className="bg-white rounded-xl border border-amber-200 p-5 flex gap-3 items-start">
          <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-slate-900">Busca não disponível</h4>
            <p className="text-sm text-slate-600 mt-1">{failure.error}</p>
            {failure.code && <p className="text-xs font-mono text-slate-500 mt-2">{failure.code}</p>}
          </div>
        </section>
      )}

      {success && (
        <section className="space-y-4">
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex gap-3 items-start">
            <CheckCircle2 className="w-5 h-5 text-emerald-700 shrink-0 mt-0.5" />
            <div className="text-sm text-emerald-900">
              <p className="font-semibold">{success.result_count} ocorrência(s) rastreável(is)</p>
              <p className="text-xs mt-1">Validação: {success.validation.mode}. Regras: {success.analysis.ruleset_version}; fonte M2: {success.analysis.source_database_sha256.slice(0, 12)}…</p>
            </div>
          </div>

          {success.results.length === 0 && (
            <div className="bg-white rounded-xl border border-dashed border-slate-300 p-10 text-center text-sm text-slate-500">
              Nenhuma ocorrência corresponde aos filtros exatos informados.
            </div>
          )}

          <div className="space-y-3">
            {success.results.map((result) => (
              <article key={result.entity.entity_id} className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-slate-900 font-mono text-sm">{result.entity.analytical_label}</p>
                    <p className="text-xs text-slate-500 mt-1">{result.entity.type} · regra {result.decision.rule_id} · confiança heurística {result.decision.confidence}</p>
                  </div>
                  <span className="text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full px-2.5 py-1">{result.decision.review_status}</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="rounded-lg bg-slate-50 border border-slate-100 p-3 space-y-1">
                    <p className="font-semibold text-slate-700 flex items-center gap-1"><Database className="w-3.5 h-3.5" /> Origem</p>
                    <p>{result.origin.relative_path}</p>
                    <p>Bloco {result.origin.block_ordinal} · candidato {result.origin.candidate_ordinal} · sentença {result.origin.sentence_id}</p>
                    <p className="font-mono break-all text-slate-500">{result.origin.block_sha256}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 border border-slate-100 p-3 space-y-1">
                    <p className="font-semibold text-slate-700 flex items-center gap-1"><FileText className="w-3.5 h-3.5" /> Âncora e decisão</p>
                    <p>{result.anchor.source_label}{result.anchor.token ? ` · ${result.anchor.token}` : ''}</p>
                    <p>{result.entity.source_projection ? `projeção-fonte ${result.entity.source_projection}` : 'sem projeção-fonte'}{result.entity.evidenced_projection ? ` · evidência ${result.entity.evidenced_projection}` : ''}</p>
                    <p className="text-slate-500">{m4ReviewNotice(result.decision)}</p>
                  </div>
                </div>

                <div className="rounded-lg border border-slate-100 p-3 text-xs space-y-2">
                  <p className="font-semibold text-slate-700">Evidências</p>
                  {result.evidence.map((evidence) => (
                    <div key={evidence.evidence_id} className="border-l-2 border-indigo-200 pl-3">
                      <p className="font-mono text-slate-700">{evidence.type} · {evidence.sha256.slice(0, 12)}…</p>
                      <p className="text-slate-500">{evidence.description}</p>
                      <pre className="mt-1 whitespace-pre-wrap break-words text-slate-600">{JSON.stringify(evidence.value)}</pre>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
