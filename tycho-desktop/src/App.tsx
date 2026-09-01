import { useState, useEffect } from "react";
import "./App.css";
import { 
  Search, 
  History, 
  Settings, 
  Database, 
  ExternalLink, 
  CheckCircle2, 
  AlertCircle, 
  ChevronRight,
  BookOpen,
  Calendar,
  Sparkles,
  RefreshCw,
  Info,
  GraduationCap,
  ShieldCheck
} from "lucide-react";
import { SearchBar } from "./components/SearchBar";
import { HumanInTheLoop } from "./components/HumanInTheLoop";
import { TreeView } from "./components/TreeView";
import { TermBreakdown } from "./components/TermBreakdown";
import { CreditsModal } from "./components/CreditsModal";
import { M4SearchPanel } from "./components/M4SearchPanel";
import { 
  searchCorpus, 
  getSystemHealth, 
  tokenizarSentenca,
  SearchResult, 
  SystemHealth,
  TokenCartografico 
} from "./services/api";

function App() {
  const [activeTab, setActiveTab] = useState<"m4" | "search" | "review" | "settings">("m4");
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [selectedTokens, setSelectedTokens] = useState<TokenCartografico[]>([]);
  const [loadingTokens, setLoadingTokens] = useState(false);
  const [showCreditsModal, setShowCreditsModal] = useState(false);

  const fetchHealth = async () => {
    setLoadingHealth(true);
    const data = await getSystemHealth();
    setHealth(data);
    setLoadingHealth(false);
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const handleSearch = async (query: string) => {
    setLoadingSearch(true);
    setSelectedResult(null);
    setSelectedTokens([]);
    const results = await searchCorpus(query);
    setSearchResults(results);
    if (results.length > 0) {
      handleSelectResult(results[0]);
    }
    setLoadingSearch(false);
  };

  const handleSelectResult = async (item: SearchResult) => {
    setSelectedResult(item);
    setLoadingTokens(true);
    const rawTree = typeof item.arvore === "string" ? item.arvore : JSON.stringify(item.arvore);
    const tokens = await tokenizarSentenca(rawTree);
    setSelectedTokens(tokens);
    setLoadingTokens(false);
  };

  // Helper para converter nó de árvore em formato compatível com react-d3-tree
  const formatTreeForD3 = (treeData: any): any => {
    if (!treeData) return { name: "Vazio", children: [] };
    if (typeof treeData === "string") return { name: treeData, children: [] };
    if (treeData.name) return treeData;
    if (Array.isArray(treeData)) {
      return {
        name: "Raiz",
        children: treeData.map(formatTreeForD3)
      };
    }
    return { name: JSON.stringify(treeData), children: [] };
  };

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Modal de Créditos Acadêmicos */}
      <CreditsModal isOpen={showCreditsModal} onClose={() => setShowCreditsModal(false)} />

      {/* Sidebar */}
      <aside className="w-72 bg-white border-r border-slate-200 flex flex-col justify-between shadow-sm">
        <div>
          {/* Logo / Header */}
          <div className="p-5 border-b border-slate-100 flex items-center gap-3">
            <div className="p-2 bg-indigo-600 rounded-lg text-white shadow-md shadow-indigo-100">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-bold text-base text-slate-900 leading-tight">Tycho Brahe</h1>
              <p className="text-xs text-slate-500 font-medium">Pesquisa Sintática Gerativa</p>
            </div>
          </div>
          
          {/* Navigation */}
          <nav className="p-3 space-y-1">
            <button
              onClick={() => setActiveTab("m4")}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                activeTab === "m4"
                  ? "bg-indigo-50 text-indigo-700 font-semibold shadow-xs"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <div className="flex items-center gap-3">
                <ShieldCheck className="w-4 h-4" />
                <span>Busca Evidencial (M4)</span>
              </div>
            </button>

            <button 
              onClick={() => setActiveTab("search")}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                activeTab === "search" 
                  ? "bg-indigo-50 text-indigo-700 font-semibold shadow-xs" 
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <div className="flex items-center gap-3">
                <Search className="w-4 h-4" />
                <span>Consulta Histórica</span>
              </div>
              {searchResults.length > 0 && (
                <span className="text-xs bg-indigo-200/60 text-indigo-800 px-2 py-0.5 rounded-full font-bold">
                  {searchResults.length}
                </span>
              )}
            </button>

            <button 
              onClick={() => setActiveTab("review")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                activeTab === "review" 
                  ? "bg-indigo-50 text-indigo-700 font-semibold shadow-xs" 
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <History className="w-4 h-4" />
              <span>Auditoria (Quarentena)</span>
            </button>

            <button 
              onClick={() => setActiveTab("settings")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                activeTab === "settings" 
                  ? "bg-indigo-50 text-indigo-700 font-semibold shadow-xs" 
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Status do Sistema</span>
            </button>
          </nav>
        </div>

        {/* Footer & Créditos */}
        <div className="p-4 border-t border-slate-100 space-y-3 bg-slate-50/50">
          {/* Status Badge */}
          <div className="p-3 bg-white border border-slate-200 rounded-lg shadow-2xs text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-700">Motor Rust Core</span>
              <span className={`inline-flex items-center gap-1 font-medium ${health?.engine_status === 'ONLINE' ? 'text-emerald-600' : 'text-amber-600'}`}>
                {health?.engine_status === 'ONLINE' ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
                {health?.engine_status || 'Verificando...'}
              </span>
            </div>
            <div className="flex items-center justify-between text-slate-500 text-[11px]">
              <span>Banco Corpus</span>
              <span>{health?.db_exists ? "Conectado" : "Pendente"}</span>
            </div>
          </div>

          {/* Institutional Credit & Link */}
          <div className="text-[11px] text-slate-500 leading-relaxed pt-1 space-y-1.5">
            <p>
              <span className="font-semibold text-slate-700">Plataforma Tycho Brahe © 2026</span>, criada e desenvolvida principalmente por Luiz Henrique Lima Veronesi (IEL/UNICAMP).
            </p>
            <div className="flex items-center justify-between pt-1">
              <button
                onClick={() => setShowCreditsModal(true)}
                className="text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center gap-1 cursor-pointer transition-colors"
              >
                <GraduationCap className="w-3.5 h-3.5" />
                <span>Ver referências</span>
              </button>
              <a 
                href="https://www.tycho.iel.unicamp.br/"
                target="_blank" 
                rel="noreferrer"
                className="text-slate-400 hover:text-slate-700 inline-flex items-center gap-1 transition-colors"
                title="Acessar portal da Plataforma Tycho Brahe"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between shadow-2xs">
          <div>
            <h2 className="text-lg font-bold text-slate-800">
              {activeTab === "m4" && "Busca Evidencial Rastreável"}
              {activeTab === "search" && "Consulta Histórica & Visualização Legada"}
              {activeTab === "review" && "Painel Human-in-the-Loop (Auditoria de Expansão)"}
              {activeTab === "settings" && "Diagnóstico & Configurações do Motor"}
            </h2>
            <p className="text-xs text-slate-500">
              {activeTab === "m4" && "Consulta parametrizada sobre evidências Marco 3 promovidas, com origem e regras verificáveis."}
              {activeTab === "search" && "Fluxo histórico preservado para auditoria; não corresponde à rota de busca Marco 4."}
              {activeTab === "review" && "Revise anomalias e valide regras de reescrita cartográfica de forma supervisionada."}
              {activeTab === "settings" && "Verifique a integridade do SQLite, conexões IPC e versão dos binários."}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowCreditsModal(true)}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Info className="w-3.5 h-3.5 text-indigo-600" />
              <span>Créditos & Teoria</span>
            </button>
            <button 
              onClick={fetchHealth}
              disabled={loadingHealth}
              title="Atualizar diagnóstico"
              className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${loadingHealth ? "animate-spin" : ""}`} />
            </button>
          </div>
        </header>
        
        {/* Body Container */}
        <div className="flex-1 p-6 overflow-auto">
          {activeTab === "m4" && <M4SearchPanel />}

          {activeTab === "search" && (
            <div className="space-y-6 max-w-7xl mx-auto">
              {/* Search Card */}
              <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-6">
                <SearchBar onSearch={handleSearch} />
              </div>

              {/* Status de Carregamento */}
              {loadingSearch && (
                <div className="flex flex-col items-center justify-center py-16 text-slate-500 gap-3">
                  <RefreshCw className="w-7 h-7 animate-spin text-indigo-600" />
                  <p className="text-sm font-medium">Buscando árvores no corpus histórico...</p>
                </div>
              )}

              {/* Resultados */}
              {!loadingSearch && searchResults.length > 0 && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                  {/* Lista de Sentenças (4 Colunas) */}
                  <div className="lg:col-span-4 space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Ocorrências encontradas ({searchResults.length})
                    </h3>
                    <div className="space-y-2.5 max-h-[680px] overflow-y-auto pr-1">
                      {searchResults.map((item) => (
                        <div
                          key={item.id}
                          onClick={() => handleSelectResult(item)}
                          className={`p-4 rounded-xl border transition-all cursor-pointer ${
                            selectedResult?.id === item.id 
                              ? "bg-indigo-50/70 border-indigo-300 ring-1 ring-indigo-300 shadow-xs" 
                              : "bg-white border-slate-200 hover:border-slate-300 hover:shadow-2xs"
                          }`}
                        >
                          <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5">
                            <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                              <BookOpen className="w-3.5 h-3.5 text-slate-400" />
                              {item.autor || item.texto || "Doc"}
                            </span>
                            {item.ano && (
                              <span className="flex items-center gap-1 font-medium">
                                <Calendar className="w-3 h-3 text-slate-400" />
                                {item.ano}
                              </span>
                            )}
                          </div>
                          
                          <p className="text-sm text-slate-800 line-clamp-2 leading-relaxed font-serif">
                            "{item.frase || "Sentença anotada"}"
                          </p>

                          <div className="mt-3 flex items-center justify-between pt-2 border-t border-slate-100">
                            {item.eh_cartografico ? (
                              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-700 bg-indigo-100/70 px-2 py-0.5 rounded-md">
                                <Sparkles className="w-3 h-3" /> Cartografia 5D
                              </span>
                            ) : (
                              <span className="text-[11px] text-slate-400 font-medium">Sintaxe Original</span>
                            )}
                            <ChevronRight className="w-4 h-4 text-slate-400" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Visualizador de Árvore e Tabela Termo a Termo (8 Colunas) */}
                  <div className="lg:col-span-8 space-y-6 flex flex-col">
                    {/* Visualizador de Árvore D3 */}
                    <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-6 flex flex-col">
                      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
                        <div>
                          <h4 className="font-bold text-slate-800 text-sm">
                            Representação Estrutural (Árvore Hierárquica D3)
                          </h4>
                          <p className="text-xs text-slate-500">
                            {selectedResult ? `ID Sentença: ${selectedResult.id} | ${selectedResult.autor || ''}` : "Selecione uma ocorrência para inspecionar nós"}
                          </p>
                        </div>
                        {selectedResult?.eh_cartografico && (
                          <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs px-2.5 py-1 rounded-full font-semibold flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Nós Cartográficos Identificados
                          </span>
                        )}
                      </div>

                      <div className="flex-1">
                        {selectedResult ? (
                          <TreeView data={formatTreeForD3(selectedResult.arvore)} />
                        ) : (
                          <div className="h-48 flex items-center justify-center text-slate-400 text-sm">
                            Nenhuma sentença selecionada
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Tabela de Detalhamento Termo a Termo */}
                    {selectedResult && (
                      <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-6">
                        <TermBreakdown tokens={selectedTokens} loading={loadingTokens} />
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Mensagem Inicial / Vazia */}
              {!loadingSearch && searchResults.length === 0 && (
                <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center max-w-2xl mx-auto space-y-3">
                  <div className="w-12 h-12 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
                    <Search className="w-6 h-6" />
                  </div>
                  <h3 className="font-semibold text-slate-800 text-base">Nenhuma pesquisa ativa</h3>
                  <p className="text-sm text-slate-500 max-w-md mx-auto leading-relaxed">
                    Clique em um dos chips rápidos dos 5 domínios ou digite uma categoria sintática (ex: <code className="bg-slate-100 px-1.5 py-0.5 rounded text-indigo-700 font-mono text-xs">ForceP</code>, <code className="bg-slate-100 px-1.5 py-0.5 rounded text-indigo-700 font-mono text-xs">VocP</code>, <code className="bg-slate-100 px-1.5 py-0.5 rounded text-indigo-700 font-mono text-xs">T_anterior</code>, <code className="bg-slate-100 px-1.5 py-0.5 rounded text-indigo-700 font-mono text-xs">VoiceP_agent</code>) para consultar o corpus.
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === "review" && (
            <div className="max-w-6xl mx-auto">
              <HumanInTheLoop />
            </div>
          )}

          {activeTab === "settings" && (
            <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-xs border border-slate-200 p-6 space-y-6">
              <div>
                <h3 className="text-base font-bold text-slate-900">Diagnóstico da Arquitetura</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Validação de ponta a ponta: React UI &rarr; Tauri Rust Motor &rarr; Python Backend Sidecar &rarr; SQLite.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Motor Nativo (Rust)</span>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-800">Status</span>
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                      {health?.engine_status || "OFFLINE"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-600">
                    <span>Sistema Operacional</span>
                    <span>{health?.os_info || "Desconhecido"}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-600">
                    <span>Versão da Aplicação</span>
                    <span>v{health?.app_version || "0.1.0"}</span>
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Armazenamento & Corpus</span>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-800">Banco SQLite (Fase 3)</span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${health?.db_exists ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                      {health?.db_exists ? "Detectado" : "Ausente"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-800">Banco Cartografia</span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${health?.cartografia_db_exists ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                      {health?.cartografia_db_exists ? "Detectado" : "Ausente"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 text-xs font-mono text-slate-600 break-all space-y-1">
                <p className="font-semibold text-slate-700">Caminho do Banco Detectado:</p>
                <p className="text-slate-500">{health?.db_path || "Nenhum caminho resolvido"}</p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
