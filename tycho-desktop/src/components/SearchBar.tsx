import { useState, FormEvent } from 'react';
import { Search, Filter, AlertCircle, CheckCircle2 } from 'lucide-react';

interface SearchBarProps {
  onSearch: (query: string) => void;
}

const QUICK_FILTERS = [
  { label: 'D1: VocP', query: 'VocP', color: 'hover:border-purple-300 hover:text-purple-700' },
  { label: 'D2: ForceP', query: 'ForceP', color: 'hover:border-blue-300 hover:text-blue-700' },
  { label: 'D2: FocP', query: 'FocP', color: 'hover:border-blue-300 hover:text-blue-700' },
  { label: 'D3: MoodP_eval', query: 'MoodP_evaluative', color: 'hover:border-emerald-300 hover:text-emerald-700' },
  { label: 'D3: T_anterior', query: 'T_anterior', color: 'hover:border-emerald-300 hover:text-emerald-700' },
  { label: 'D4: FocP_low', query: 'FocP_low', color: 'hover:border-amber-300 hover:text-amber-700' },
  { label: 'D5: VoiceP_agent', query: 'VoiceP_agent', color: 'hover:border-rose-300 hover:text-rose-700' },
  { label: 'D5: ApplP_low', query: 'ApplP_low', color: 'hover:border-rose-300 hover:text-rose-700' },
  { label: 'D5: Root', query: 'Root', color: 'hover:border-rose-300 hover:text-rose-700' },
];

export function SearchBar({ onSearch }: SearchBarProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  const handleChipClick = (filterQuery: string) => {
    setQuery(filterQuery);
    onSearch(filterQuery);
  };

  // Verificador simples de balanceamento de colchetes
  const countOpen = (query.match(/\[/g) || []).length;
  const countClose = (query.match(/\]/g) || []).length;
  const isBracketValid = countOpen === countClose;

  return (
    <div className="w-full space-y-3.5">
      <form onSubmit={handleSubmit} className="flex gap-2.5">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <Search className="h-4 w-4" />
          </div>
          <input
            type="text"
            className={`block w-full pl-10 pr-10 py-2.5 border rounded-xl text-sm transition-all shadow-2xs font-mono ${
              isBracketValid
                ? 'border-slate-300 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100'
                : 'border-amber-300 focus:border-amber-500 focus:ring-2 focus:ring-amber-100'
            }`}
            placeholder="Digite um nó ou padrão: ex. ForceP, VocP, T_anterior, VoiceP_agent..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {query.includes('[') && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              {isBracketValid ? (
                <span title="Colchetes balanceados"><CheckCircle2 className="w-4 h-4 text-emerald-500" /></span>
              ) : (
                <span title="Colchetes não balanceados"><AlertCircle className="w-4 h-4 text-amber-500" /></span>
              )}
            </div>
          )}
        </div>
        <button
          type="submit"
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-medium rounded-xl shadow-xs transition-all flex items-center gap-2 text-sm cursor-pointer"
        >
          <span>Consultar</span>
        </button>
      </form>

      {/* Chips Rápidos dos 5 Domínios */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-600">
        <span className="font-semibold text-slate-500 flex items-center gap-1 mr-1 text-[11px] uppercase tracking-wider">
          <Filter className="w-3 h-3 text-indigo-600" /> Domínios:
        </span>
        {QUICK_FILTERS.map((f) => (
          <button
            key={f.label}
            type="button"
            onClick={() => handleChipClick(f.query)}
            className={`px-2.5 py-1 bg-white border border-slate-200 rounded-lg text-[11px] font-medium transition-all shadow-3xs cursor-pointer ${f.color}`}
          >
            {f.label}
          </button>
        ))}
      </div>
    </div>
  );
}
