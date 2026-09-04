import { useState, useEffect } from "react";
import "./App.css";
import { 
  Search, 
  History, 
  Settings, 
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
    <div className="tycho-shell flex h-screen text-slate-900 font-sans">
      {/* Modal de Créditos Acadêmicos */}
      <CreditsModal isOpen={showCreditsModal} onClose={() => setShowCreditsModal(false)} />

      {/* Sidebar */}
      <aside className="tycho-sidebar w-72 bg-white border-r border-indigo-100 flex flex-col justify-between">
        <div>
          {/* Logo / Header */}
          <div className="p-5 border-b border-indigo-100 flex items-center gap-3">
            <div className="w-11 h-11 rounded-full bg-indigo-50 border border-indigo-100 p-0.5 shadow-sm">
              <img src="/tycho-brahe-mark-square.png" alt="Marca Tycho Brahe" className="w-full h-full object-contain" />
            </div>
            <div>
              <h1 className="font-display font-bold text-lg text-slate-900 leading-tight">Tycho Brahe</h1>
              <p className="tycho-eyebrow mt-1">Pesquisa sintática</p>
            </div>
          </div>
          
          {/* Navigation */}
          <nav className="p-3 space-y-1">
            <button
              onClick={() => setActiveTab("m4")}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                activeTab === "m4"
                  ? "tycho-nav-active font-semibold shadow-xs"
                  : "tycho-nav-item"
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
                  ? "tycho-nav-active font-semibold shadow-xs"
                  : "tycho-nav-item"
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
                  ? "tycho-nav-active font-semibold shadow-xs"
                  : "tycho-nav-item"
              }`}
            >
              <History className="w-4 h-4" />
              <span>Auditoria (Quarentena)</span>
            </button>

            <button 
              onClick={() => setActiveTab("settings")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                activeTab === "settings" 
                  ? "tycho-nav-active font-semibold shadow-xs"
                  : "tycho-nav-item"
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Status do Sistema</span>
            </button>
          </nav>
        </div>

        {/* Footer & Créditos */}
        <div className="p-4 border-t border-indigo-100 space-y-3 bg-indigo-50/35">
          {/* Status Badge */}
          <div className="tycho-card p-3 bg-white border text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-700">Motor Rust Core</span>
              <span className={`inline-flex items-center gap-1 font-medium ${health?.engine_status === 'ONLINE' ? 'text-emerald-600' : 'text-amber-600'}`}>
                {health?.engine_status === 'ONLINE' ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
                {health?.engine_status || 'Verificando...'}
              </span>
            </div>
            <div className="flex items-center justify-between text-slate-500 text-[11px]">
              <span>Artefato M3</span>
              <span>{health?.m4_artifact_available ? "Localizado" : "Pendente"}</span>
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
        <header className="bg-white/95 border-b border-indigo-100 px-7 py-4 flex items-center justify-between shadow-2xs">
          <div>
            <p className="tycho-eyebrow mb-1">Plataforma de pesquisa · IEL/UNICAMP</p>
            <h2 className="font-display text-xl font-bold text-slate-800">
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
        <div className="flex-1 p-7 overflow-auto">
          {activeTab === "m4" && <M4SearchPanel />}

          {activeTab === "search" && (
            <div className="space-y-6 max-w-7xl mx-auto">
              {/* Search Card */}
              <div className="tycho-card bg-white border p-6">
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
            <div className="tycho-card max-w-4xl mx-auto bg-white border p-6 space-y-6">
              <div>
                <h3 className="font-display text-xl font-bold text-slate-900">Diagnóstico da Arquitetura</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Estado local do motor, do artefato M3 controlado e das referências históricas opcionais.
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
                    <span>v{health?.app_version || "0.2.0"}</span>
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Busca Evidencial (M4)</span>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-800">Artefato M3 controlado</span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${health?.m4_artifact_available ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                      {health?.m4_artifact_available ? "Localizado" : "Pendente"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    O arquivo não acompanha o bundle; provisione um M3 validado para habilitar a busca rastreável.
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Referências Históricas</span>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-800">Fase 3 legada</span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${health?.legacy_fase3_available ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-700"}`}>
                      {health?.legacy_fase3_available ? "Disponível" : "Não instalada"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-800">Cartografia legada</span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${health?.legacy_cartography_available ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-700"}`}>
                      {health?.legacy_cartography_available ? "Disponível" : "Não instalada"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Opcional para auditoria histórica; a rota M4 não usa esses bancos como fallback.
                  </p>
                </div>
              </div>

              <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 text-xs font-mono text-slate-600 break-all space-y-1">
                <p className="font-semibold text-slate-700">Local controlado esperado para o artefato M3:</p>
                <p className="text-slate-500">{health?.m4_artifact_path || "Aguardando o diagnóstico do aplicativo"}</p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
