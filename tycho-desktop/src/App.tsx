import { useState } from "react";
import "./App.css";
import { Search, History, Settings, FileText, Database } from "lucide-react";
import { SearchBar } from "./components/SearchBar";
import { HumanInTheLoop } from "./components/HumanInTheLoop";
// import { invoke } from "@tauri-apps/api/core";

function App() {
  const [activeTab, setActiveTab] = useState("search");

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900 font-sans">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200 flex items-center gap-2">
          <Database className="w-6 h-6 text-indigo-600" />
          <h1 className="font-bold text-lg text-indigo-900">Tycho Brahe</h1>
        </div>
        
        <nav className="flex-1 p-4 space-y-1">
          <button 
            onClick={() => setActiveTab("search")}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === "search" ? "bg-indigo-50 text-indigo-700" : "text-gray-600 hover:bg-gray-100"}`}
          >
            <Search className="w-4 h-4" />
            Pesquisa Sintática
          </button>
          <button 
            onClick={() => setActiveTab("review")}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === "review" ? "bg-indigo-50 text-indigo-700" : "text-gray-600 hover:bg-gray-100"}`}
          >
            <History className="w-4 h-4" />
            Quarentena (Auditoria)
          </button>
          <button 
            onClick={() => setActiveTab("corpus")}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === "corpus" ? "bg-indigo-50 text-indigo-700" : "text-gray-600 hover:bg-gray-100"}`}
          >
            <FileText className="w-4 h-4" />
            Gerenciar Corpus
          </button>
        </nav>
        
        <div className="p-4 border-t border-gray-200">
          <button className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors">
            <Settings className="w-4 h-4" />
            Configurações
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white border-b border-gray-200 p-4">
          <h2 className="text-xl font-semibold text-gray-800">
            {activeTab === "search" && "Busca Cartográfica"}
            {activeTab === "review" && "Auditoria Human-in-the-Loop"}
            {activeTab === "corpus" && "Gerenciador de Corpus"}
          </h2>
        </header>
        
        <div className="flex-1 p-6 overflow-auto">
          {activeTab === "search" && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <SearchBar onSearch={(query) => console.log("Pesquisar por:", query)} />
              <div className="mt-8 text-center text-gray-500">
                Os resultados da pesquisa aparecerão aqui.
              </div>
            </div>
          )}
          {activeTab === "review" && (
            <HumanInTheLoop />
          )}
          {activeTab === "corpus" && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <p className="text-gray-500">Módulo de gerenciamento será implementado aqui.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
