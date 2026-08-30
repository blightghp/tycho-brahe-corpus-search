import React from 'react';
import { TokenCartografico } from '../services/api';
import { Layers } from 'lucide-react';

interface TermBreakdownProps {
  tokens: TokenCartografico[];
  loading?: boolean;
}

const DOMAIN_BADGES: Record<number, { name: string; bg: string; text: string; border: string }> = {
  1: { name: 'D1: Ato de Fala', bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
  2: { name: 'D2: Split-CP', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  3: { name: 'D3: Split-IP', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  4: { name: 'D4: Baixa Periferia', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  5: { name: 'D5: Split-vP', bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
};

export const TermBreakdown: React.FC<TermBreakdownProps> = ({ tokens, loading }) => {
  if (loading) {
    return (
      <div className="py-8 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
        <span className="w-3.5 h-3.5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></span>
        <span>Processando grade de traços cartográficos...</span>
      </div>
    );
  }

  if (!tokens || tokens.length === 0) {
    return (
      <div className="py-6 text-center text-slate-400 text-xs border border-dashed border-slate-200 rounded-lg">
        Nenhum detalhamento termo a termo disponível para esta sentença.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h5 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-indigo-600" />
          <span>Etiquetação Sintática e Funcional Termo a Termo</span>
        </h5>
        <span className="text-[11px] text-slate-400 font-medium">{tokens.length} constituintes analisados</span>
      </div>

      <div className="border border-slate-200 rounded-xl overflow-hidden shadow-2xs bg-white">
        <div className="overflow-x-auto max-h-[300px]">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold sticky top-0 z-10">
              <tr>
                <th className="py-2.5 px-3 w-8">#</th>
                <th className="py-2.5 px-3 font-bold text-slate-800">Termo</th>
                <th className="py-2.5 px-3">Lema</th>
                <th className="py-2.5 px-3">POS</th>
                <th className="py-2.5 px-3">Domínio Gerativo</th>
                <th className="py-2.5 px-3">Projeção</th>
                <th className="py-2.5 px-3">Papel Estrutural / Teórico</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {tokens.map((t) => {
                const domBadge = DOMAIN_BADGES[t.dominio_id] || {
                  name: `D${t.dominio_id}`,
                  bg: 'bg-slate-50',
                  text: 'text-slate-600',
                  border: 'border-slate-200',
                };

                return (
                  <tr key={t.indice} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-2 px-3 text-slate-400 font-mono text-[11px]">{t.indice}</td>
                    <td className="py-2 px-3 font-semibold text-slate-900">{t.termo}</td>
                    <td className="py-2 px-3 text-slate-600 italic">{t.lema}</td>
                    <td className="py-2 px-3 font-mono text-[11px]">
                      <span className="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded border border-slate-200">
                        {t.pos}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold border ${domBadge.bg} ${domBadge.text} ${domBadge.border}`}
                      >
                        {domBadge.name}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono text-[11px] font-bold text-indigo-900">
                      {t.projecao}
                    </td>
                    <td className="py-2 px-3 text-slate-600 text-[11px] leading-snug">
                      {t.papel_gerativo}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
