import { useState } from 'react';
import Tree from 'react-d3-tree';
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

interface TreeViewProps {
  data: any;
}

// Cores temáticas para os 5 Domínios Cartográficos
const DOMAIN_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  // Domínio 1: Ato de Fala (Violeta)
  SAP: { bg: '#8b5cf6', border: '#7c3aed', text: '#ffffff' },
  VocP: { bg: '#a855f7', border: '#9333ea', text: '#ffffff' },
  EvalP: { bg: '#c084fc', border: '#a855f7', text: '#ffffff' },

  // Domínio 2: Split-CP (Índigo / Azul)
  ForceP: { bg: '#3b82f6', border: '#2563eb', text: '#ffffff' },
  TopP: { bg: '#60a5fa', border: '#3b82f6', text: '#ffffff' },
  TopP_fam: { bg: '#93c5fd', border: '#60a5fa', text: '#1e3a8a' },
  IntP: { bg: '#2563eb', border: '#1d4ed8', text: '#ffffff' },
  FocP: { bg: '#1d4ed8', border: '#1e40af', text: '#ffffff' },
  ModP: { bg: '#38bdf8', border: '#0284c7', text: '#0c4a6e' },
  QembP: { bg: '#0284c7', border: '#0369a1', text: '#ffffff' },
  FinP: { bg: '#4f46e5', border: '#4338ca', text: '#ffffff' },

  // Domínio 3: Split-IP / Cinque (Esmeralda / Verde)
  MoodP: { bg: '#10b981', border: '#059669', text: '#ffffff' },
  ModP_epistemic: { bg: '#34d399', border: '#10b981', text: '#064e3b' },
  T_past: { bg: '#059669', border: '#047857', text: '#ffffff' },
  T_future: { bg: '#059669', border: '#047857', text: '#ffffff' },
  T_anterior: { bg: '#047857', border: '#065f46', text: '#ffffff' },
  AspP: { bg: '#6ee7b7', border: '#34d399', text: '#064e3b' },
  CoreIP: { bg: '#059669', border: '#047857', text: '#ffffff' },

  // Domínio 4: Baixa Periferia (Âmbar / Laranja)
  TopP_low: { bg: '#f59e0b', border: '#d97706', text: '#ffffff' },
  FocP_low: { bg: '#ea580c', border: '#c2410c', text: '#ffffff' },

  // Domínio 5: Split-vP / First Phase (Rosa / Carmim)
  VoiceP_agent: { bg: '#f43f5e', border: '#e11d48', text: '#ffffff' },
  InitP: { bg: '#fb7185', border: '#f43f5e', text: '#881337' },
  ApplP_high: { bg: '#fda4af', border: '#fb7185', text: '#881337' },
  ProcP: { bg: '#e11d48', border: '#be123c', text: '#ffffff' },
  ApplP_low: { bg: '#fda4af', border: '#fb7185', text: '#881337' },
  ResP: { bg: '#9f1239', border: '#881337', text: '#ffffff' },
  Root: { bg: '#881337', border: '#4c0519', text: '#ffffff' },
};

function getNodeColor(label: string) {
  for (const [key, val] of Object.entries(DOMAIN_COLORS)) {
    if (label === key || label.startsWith(key + '_') || label.startsWith(key + '-')) {
      return val;
    }
  }
  // Nós canônicos tradicionais (CP, IP, VP, NP, etc.)
  if (label.startsWith('CP')) return { bg: '#e0e7ff', border: '#818cf8', text: '#3730a3' };
  if (label.startsWith('IP')) return { bg: '#d1fae5', border: '#6ee7b7', text: '#065f46' };
  if (label.startsWith('VP')) return { bg: '#ffe4e6', border: '#fda4af', text: '#9f1239' };
  if (label.startsWith('NP')) return { bg: '#f1f5f9', border: '#cbd5e1', text: '#334155' };
  if (label.startsWith('PP')) return { bg: '#fef3c7', border: '#fde68a', text: '#92400e' };
  if (label.startsWith('ADV')) return { bg: '#e0f2fe', border: '#bae6fd', text: '#0369a1' };

  return { bg: '#f8fafc', border: '#e2e8f0', text: '#475569' };
}

export function TreeView({ data }: TreeViewProps) {
  const [zoom, setZoom] = useState(1);
  const [translate, setTranslate] = useState({ x: 340, y: 60 });

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.2, 2.5));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.2, 0.4));
  const handleReset = () => {
    setZoom(1);
    setTranslate({ x: 340, y: 60 });
  };

  return (
    <div className="relative w-full h-[520px] border border-slate-200 rounded-xl bg-slate-50/50 overflow-hidden shadow-inner flex flex-col">
      {/* Controles Flutuantes de Zoom / Pan */}
      <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5 bg-white/95 backdrop-blur-xs border border-slate-200 p-1.5 rounded-lg shadow-xs">
        <button
          onClick={handleZoomIn}
          title="Aproximar Zoom"
          className="p-1.5 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors cursor-pointer"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={handleZoomOut}
          title="Afastar Zoom"
          className="p-1.5 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors cursor-pointer"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleReset}
          title="Resetar Vista"
          className="p-1.5 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors cursor-pointer"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Legenda dos 5 Domínios */}
      <div className="absolute bottom-2 left-3 z-10 flex items-center gap-3 bg-white/90 backdrop-blur-xs border border-slate-200 px-3 py-1.5 rounded-lg shadow-2xs text-[10px] text-slate-600 font-medium">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-500"></span> D1: Ato Fala</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span> D2: Split-CP</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> D3: Split-IP</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500"></span> D4: Baixa Perif.</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-rose-500"></span> D5: Split-vP</span>
      </div>

      {/* Canvas SVG Interativo D3 */}
      <div className="flex-1 w-full h-full">
        <Tree
          data={data}
          orientation="vertical"
          pathFunc="step"
          zoom={zoom}
          translate={translate}
          nodeSize={{ x: 130, y: 75 }}
          separation={{ siblings: 1.1, nonSiblings: 1.3 }}
          renderCustomNodeElement={({ nodeDatum, toggleNode }) => {
            const label = nodeDatum.name || '';
            const color = getNodeColor(label);

            return (
              <g onClick={toggleNode} className="cursor-pointer select-none">
                <rect
                  x="-42"
                  y="-14"
                  width="84"
                  height="28"
                  rx="6"
                  fill={color.bg}
                  stroke={color.border}
                  strokeWidth="1.5"
                  className="transition-all hover:filter hover:brightness-110"
                />
                <text
                  fill={color.text}
                  fontSize="11"
                  fontWeight="600"
                  fontFamily="monospace"
                  textAnchor="middle"
                  dy="4"
                >
                  {label.length > 11 ? label.substring(0, 10) + '…' : label}
                </text>
              </g>
            );
          }}
        />
      </div>
    </div>
  );
}
