import React from 'react';
import { X, ExternalLink, BookOpen, GraduationCap, Globe } from 'lucide-react';

interface CreditsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CreditsModal: React.FC<CreditsModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
      <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-2xl max-h-[90vh] overflow-y-auto flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white z-10">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-50 border border-indigo-100 rounded-xl text-indigo-600">
              <GraduationCap className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-900">Créditos e Referências Teóricas</h3>
              <p className="text-xs text-slate-500">Corpus Histórico Tycho Brahe & Programa Cartográfico</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 text-xs text-slate-600 leading-relaxed">
          {/* O Projeto Tycho Brahe */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
              <Globe className="w-4 h-4 text-indigo-600" />
              <span>O Projeto Corpus Tycho Brahe</span>
            </div>
            <p>
              O <strong>Tycho Brahe Parsed Corpus of Historical Portuguese</strong> é um corpus eletrônico anotado de textos em português histórico (séculos XIV a XIX), desenvolvido no Instituto de Estudos da Linguagem (IEL) da Universidade Estadual de Campinas (UNICAMP).
            </p>
            <div className="pt-2">
              <a
                href="http://www.tycho.iel.unicamp.br/"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-indigo-600 hover:text-indigo-800 font-semibold transition-colors"
              >
                <span>Acessar portal oficial: http://www.tycho.iel.unicamp.br/</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          {/* Fundamentação Teórica dos 5 Domínios */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
              <BookOpen className="w-4 h-4 text-indigo-600" />
              <span>Fundamentação do Programa Cartográfico Gerativo</span>
            </div>
            <ul className="space-y-2 pl-2">
              <li className="p-2.5 rounded-lg border border-slate-100 bg-white shadow-3xs">
                <strong>1. Domínio do Ato de Fala:</strong> Speas, P., & Tenny, C. (2003). <em>Configurational properties of point of view roles</em>; Hill, V. (2007). <em>Vocatives and the speech act tier</em>.
              </li>
              <li className="p-2.5 rounded-lg border border-slate-100 bg-white shadow-3xs">
                <strong>2. Domínio Complementizador (Split-CP):</strong> Rizzi, L. (1997). <em>The Fine Structure of the Left Periphery</em>. In: Elements of Grammar. Kluwer, Dordrecht; Rizzi, L. (2004). <em>The Structure of CP and IP</em>.
              </li>
              <li className="p-2.5 rounded-lg border border-slate-100 bg-white shadow-3xs">
                <strong>3. Domínio Flexional (Split-IP / TP):</strong> Cinque, G. (1999). <em>Adverbs and Functional Heads: A Cross-Linguistic Perspective</em>. Oxford University Press.
              </li>
              <li className="p-2.5 rounded-lg border border-slate-100 bg-white shadow-3xs">
                <strong>4. Baixa Periferia Esquerda:</strong> Belletti, A. (2004). <em>Aspects of the Low Periphery in the Clause</em>. In: The Structure of CP and IP.
              </li>
              <li className="p-2.5 rounded-lg border border-slate-100 bg-white shadow-3xs">
                <strong>5. Domínio Temático e Argumental (Split-vP):</strong> Ramchand, G. (2008). <em>Verb Meaning and the Lexicon: A First-Phase Syntax</em>; Pylkkänen, L. (2008). <em>Introducing Arguments</em>; Harley, H. (2013).
              </li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl text-xs shadow-xs transition-colors cursor-pointer"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
};
