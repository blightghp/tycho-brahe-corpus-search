import React, { useState, useEffect } from 'react';
import { listarQuarentena, resolverQuarentena, QuarentenaItem } from '../services/api';
import { 
  Check, 
  X, 
  AlertTriangle, 
  FileText, 
  RefreshCw, 
  ChevronRight, 
  ShieldAlert, 
  CheckCircle2,
  Clock,
  Sparkles
} from 'lucide-react';

export const HumanInTheLoop: React.FC = () => {
  const [items, setItems] = useState<QuarentenaItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<QuarentenaItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const carregarDados = async () => {
    setLoading(true);
    const data = await listarQuarentena();
    setItems(data);
    if (data.length > 0) {
      setSelectedItem(data[0]);
    } else {
      setSelectedItem(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    carregarDados();
  }, []);

  const handleAction = async (id: number, acao: 'APROVAR' | 'REJEITAR') => {
    setActionLoading(true);
    const sucesso = await resolverQuarentena(id, acao);
    if (sucesso) {
      const novosItems = items.filter((item) => item.id !== id);
      setItems(novosItems);
      setSelectedItem(novosItems.length > 0 ? novosItems[0] : null);
    }
    setActionLoading(false);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner de Resumo da Auditoria */}
      <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-xl text-amber-600">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800">
              Quarentena de Sentenças & Curadoria Human-in-the-Loop
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Casos que desviaram da hierarquia rígida universal ou apresentaram ordem não-canônica no corpus.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold px-3 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            {items.length} pendentes para revisão
          </span>
          <button
            onClick={carregarDados}
            disabled={loading}
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
            title="Atualizar lista"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center text-slate-400 text-sm flex flex-col items-center gap-3">
          <RefreshCw className="w-6 h-6 animate-spin text-indigo-600" />
          <span>Carregando anomalias da quarentena...</span>
        </div>
      ) : items.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center max-w-lg mx-auto space-y-3">
          <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h4 className="font-bold text-slate-800 text-sm">Quarentena Limpa!</h4>
          <p className="text-xs text-slate-500 leading-relaxed">
            Todas as anomalias cartográficas foram revisadas ou não há pendências na base de dados.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Lista Lateral de Casos (4 Colunas) */}
          <div className="lg:col-span-4 space-y-2.5 max-h-[620px] overflow-y-auto pr-1">
            {items.map((item) => (
              <div
                key={item.id}
                onClick={() => setSelectedItem(item)}
                className={`p-4 rounded-xl border transition-all cursor-pointer ${
                  selectedItem?.id === item.id
                    ? 'bg-amber-50/60 border-amber-300 ring-1 ring-amber-300 shadow-xs'
                    : 'bg-white border-slate-200 hover:border-slate-300 hover:shadow-2xs'
                }`}
              >
                <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1.5">
                  <span className="font-semibold text-slate-700 flex items-center gap-1">
                    <FileText className="w-3.5 h-3.5 text-slate-400" />
                    {item.arquivo}
                  </span>
                  <span className="font-mono text-[10px] bg-slate-100 px-1.5 py-0.5 rounded">
                    #{item.id}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 my-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider bg-rose-50 text-rose-700 border border-rose-200 px-2 py-0.5 rounded">
                    {item.tipo_anomalia || 'ORDEM_NAO_CANONICA'}
                  </span>
                </div>

                <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                  {item.motivo_anomalia}
                </p>

                <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                  <span>ID Sentença: {item.sent_id_externo || 'N/A'}</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </div>
              </div>
            ))}
          </div>

          {/* Painel Central de Auditoria Lado-a-Lado (8 Colunas) */}
          {selectedItem && (
            <div className="lg:col-span-8 bg-white rounded-xl shadow-xs border border-slate-200 p-6 space-y-6 flex flex-col justify-between">
              <div className="space-y-5">
                {/* Header do Item Selecionado */}
                <div className="flex items-start justify-between pb-4 border-b border-slate-100">
                  <div>
                    <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                      <span>Auditoria do Item #{selectedItem.id}</span>
                      <span className="text-xs font-normal text-slate-500">({selectedItem.arquivo})</span>
                    </h4>
                    <p className="text-xs text-rose-600 font-medium mt-1 flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span>{selectedItem.motivo_anomalia}</span>
                    </p>
                  </div>
                </div>

                {/* Visualização da Árvore Original vs Sugestão */}
                <div className="space-y-4">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-1.5">
                      Estrutura Anotada Original (PSD):
                    </span>
                    <pre className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono text-slate-800 overflow-x-auto max-h-48 whitespace-pre-wrap leading-relaxed">
                      {selectedItem.arvore_original}
                    </pre>
                  </div>

                  {selectedItem.arvore_sugerida && (
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 flex items-center gap-1 mb-1.5">
                        <Sparkles className="w-3.5 h-3.5" /> Expansão Sugerida pelo Transdutor:
                      </span>
                      <pre className="p-3.5 bg-indigo-50/50 border border-indigo-200 rounded-xl text-xs font-mono text-indigo-950 overflow-x-auto max-h-48 whitespace-pre-wrap leading-relaxed">
                        {selectedItem.arvore_sugerida}
                      </pre>
                    </div>
                  )}
                </div>
              </div>

              {/* Botões de Ação do Linguista */}
              <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
                <button
                  onClick={() => handleAction(selectedItem.id, 'REJEITAR')}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 border border-slate-300 font-medium rounded-xl text-xs flex items-center gap-1.5 transition-all shadow-3xs cursor-pointer"
                >
                  <X className="w-3.5 h-3.5 text-rose-500" />
                  <span>Manter Sintaxe Clássica (Rejeitar)</span>
                </button>

                <button
                  onClick={() => handleAction(selectedItem.id, 'APROVAR')}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-medium rounded-xl text-xs flex items-center gap-1.5 transition-all shadow-xs cursor-pointer"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Aprovar Expansão Cartográfica</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
