import { useState, useEffect } from 'react';
import { Check, X, Edit3, AlertTriangle, RefreshCw } from 'lucide-react';
import { listarQuarentena, resolverQuarentena, QuarentenaItem } from '../services/api';

export function HumanInTheLoop() {
  const [quarentenaItems, setQuarentenaItems] = useState<QuarentenaItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchItems = async () => {
    setLoading(true);
    const items = await listarQuarentena();
    setQuarentenaItems(items);
    setLoading(false);
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const handleResolver = async (id: number, acao: string) => {
    const success = await resolverQuarentena(id, acao);
    if (success) {
      setQuarentenaItems(prev => prev.filter(i => i.id !== id));
    } else {
      alert("Erro ao resolver item");
    }
  };


  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <RefreshCw className="w-8 h-8 animate-spin mb-4" />
        <p>Carregando quarentena...</p>
      </div>
    );
  }

  if (quarentenaItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <Check className="w-12 h-12 text-green-500 mb-4" />
        <p className="text-lg">Fila de quarentena vazia. Bom trabalho!</p>
        <button onClick={fetchItems} className="mt-4 text-sm text-indigo-600 hover:underline flex items-center gap-2">
          <RefreshCw className="w-4 h-4" /> Atualizar
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-md flex justify-between items-center">
        <div className="flex items-center">
          <AlertTriangle className="h-6 w-6 text-yellow-600 mr-3" />
          <p className="text-yellow-800 font-medium">
            Há {quarentenaItems.length} árvore(s) aguardando auditoria cartográfica.
          </p>
        </div>
        <button onClick={fetchItems} className="text-yellow-700 hover:bg-yellow-100 p-2 rounded">
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {quarentenaItems.map((item) => (
        <div key={item.id} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-800">
              ID: {item.id} <span className="text-sm font-normal text-gray-500 ml-2">({item.arquivo})</span>
            </h3>
            <span className="px-3 py-1 bg-red-100 text-red-800 text-sm font-medium rounded-full">
              {item.tipo_anomalia}
            </span>
          </div>
          
          <div className="p-6 space-y-4">
            <div>
              <p className="text-sm text-gray-500 font-medium">Motivo (Oracle)</p>
              <p className="text-red-600 font-mono text-sm mt-1 bg-red-50 p-2 rounded">{item.motivo_anomalia}</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500 font-medium mb-2">Árvore Original (Fase 1)</p>
                <div className="bg-gray-100 p-2 rounded text-xs overflow-auto max-h-40 font-mono whitespace-pre">
                  {item.arvore_original}
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-500 font-medium mb-2">Árvore Sugerida (Fase 3)</p>
                <div className="bg-indigo-50 p-2 rounded text-xs overflow-auto max-h-40 font-mono whitespace-pre text-indigo-900">
                  {item.arvore_sugerida}
                </div>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 px-6 py-4 flex items-center justify-end gap-3 border-t border-gray-200">
            <button onClick={() => handleResolver(item.id, 'manter_original')} className="flex items-center gap-2 px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
              <X className="w-4 h-4 text-red-500" />
              Rejeitar (Manter Original)
            </button>
            <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
              <Edit3 className="w-4 h-4 text-indigo-500" />
              Ajustar Manualmente
            </button>
            <button onClick={() => handleResolver(item.id, 'aprovar_sugerida')} className="flex items-center gap-2 px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700">
              <Check className="w-4 h-4" />
              Aprovar Expansão
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
