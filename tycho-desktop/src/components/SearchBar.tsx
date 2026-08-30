import { useState, FormEvent } from 'react';
import { Search, Filter } from 'lucide-react';

interface SearchBarProps {
  onSearch: (query: string) => void;
}

export function SearchBar({ onSearch }: SearchBarProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-4">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm shadow-sm"
            placeholder="Ex: [ForceP [TopP [FocP ...]]]"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <button
          type="submit"
          className="px-6 py-3 border border-transparent text-sm font-medium rounded-lg shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          Buscar
        </button>
      </form>
      
      <div className="flex gap-2 text-sm text-gray-600">
        <span className="font-medium flex items-center gap-1">
          <Filter className="w-4 h-4" /> Sugestões:
        </span>
        <button className="hover:text-indigo-600 hover:underline cursor-pointer" onClick={() => setQuery('[TopP]')}>TopP</button>
        <span>&bull;</span>
        <button className="hover:text-indigo-600 hover:underline cursor-pointer" onClick={() => setQuery('[FocP]')}>FocP</button>
        <span>&bull;</span>
        <button className="hover:text-indigo-600 hover:underline cursor-pointer" onClick={() => setQuery('[FinP]')}>FinP</button>
      </div>
    </div>
  );
}
