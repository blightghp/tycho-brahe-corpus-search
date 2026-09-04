import React from 'react';
import { X, ExternalLink, BookOpen, GraduationCap, Globe, Users, FileText, ShieldCheck } from 'lucide-react';

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
              <h3 className="font-display font-bold text-lg text-slate-900">Créditos, Referências e Direitos</h3>
              <p className="text-xs text-slate-500">Plataforma Tycho Brahe &amp; Programa Cartográfico</p>
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

          {/* Copyright & Plataforma Tycho Brahe */}
          <div className="p-4 rounded-xl bg-indigo-50 border border-indigo-200 space-y-2">
            <div className="flex items-center gap-2 text-indigo-800 font-bold text-sm">
              <Globe className="w-4 h-4 text-indigo-600" />
              <span>Plataforma Tycho Brahe</span>
            </div>
            <p className="font-semibold text-indigo-700">
              Todos os direitos reservados à Plataforma Tycho Brahe © 2026
            </p>
            <p>
              A <strong>Plataforma Tycho Brahe</strong> foi criada e desenvolvida principalmente por <strong>Luiz Henrique Lima Veronesi</strong> como fruto de sua pesquisa de doutorado em Linguística na UNICAMP, sob orientação da <strong>Professora Dra. Charlotte Galves</strong>, do Instituto de Estudos da Linguagem (IEL/UNICAMP).
            </p>
            <p>
              A plataforma consiste em um conjunto de ferramentas digitais para gestão, anotação, análises sintáticas e morfológicas de corpora linguísticos.
            </p>
            <div className="pt-2 space-y-1">
              <a
                href="https://www.tycho.iel.unicamp.br/"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-indigo-600 hover:text-indigo-800 font-semibold transition-colors"
              >
                <span>Portal Tycho Brahe: tycho.iel.unicamp.br</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          {/* Termos oficiais do corpus */}
          <div className="p-4 rounded-xl bg-indigo-50 border border-indigo-200 space-y-2">
            <div className="flex items-center gap-2 text-indigo-800 font-bold text-sm">
              <ShieldCheck className="w-4 h-4 text-indigo-600" />
              <span>Termos oficiais do Corpus Histórico do Português Tycho Brahe</span>
            </div>
            <p>
              O instalador desta prévia técnica não inclui o corpus, bancos M2/M3 ou credenciais, nem concede direito de acesso a eles. Todo uso de dados do corpus depende dos termos oficiais publicados pelo portal original.
            </p>
            <p>
              Ao aceitar o instalador, a pessoa usuária reconhece que o corpus não está em domínio público, que o uso é acadêmico ou pedagógico e que as restrições de redistribuição, uso comercial, senhas e citação devem ser observadas conforme a fonte vinculante.
            </p>
            <div className="pt-2">
              <a
                href="https://www.tycho.iel.unicamp.br/corpus/termos.html"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-indigo-600 hover:text-indigo-800 font-semibold transition-colors"
              >
                <span>Abrir termos oficiais do corpus</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          {/* Referência da Tese */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
              <FileText className="w-4 h-4 text-indigo-600" />
              <span>Referência Principal</span>
            </div>
            <p className="italic">
              VERONESI, Luiz Henrique Lima. <em>A Plataforma Tycho Brahe: um sistema para corpora sintaticamente anotados</em>. 2026. 211 f. Tese (Doutorado em Linguística) — Instituto de Estudos da Linguagem, Universidade Estadual de Campinas, Campinas, 2026.
            </p>
            <div className="pt-1">
              <a
                href="https://www.tycho.iel.unicamp.br/upload/Luiz_Veronesi_A_Plataforma_Tycho_Brahe_Tese_2026.pdf"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-indigo-600 hover:text-indigo-800 font-semibold transition-colors"
              >
                <span>Acessar tese completa (PDF)</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          {/* DACILAT */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
              <Users className="w-4 h-4 text-indigo-600" />
              <span>DACILAT — Participantes e Colaboradores</span>
            </div>
            <p>
              O <strong>DACILAT</strong> (Corpora Anotados Digitais de Línguas Indígenas Brasileiras com Traduções Automáticas) é um projeto científico de documentação digital para a preservação e análise de línguas nativas do Brasil. A Plataforma Tycho Brahe é um projeto associado ao DACILAT, e os corpora construídos pelo grupo ajudam a alimentar a Plataforma.
            </p>
            <div className="grid grid-cols-2 gap-1 pt-2">
              <span className="font-semibold">Maria Filomena Sandalo</span><span className="text-slate-500">Coordenadora</span>
              <span className="font-semibold">Charlotte Galves</span><span className="text-slate-500">Pesquisadora Principal</span>
              <span className="font-semibold">Pablo Feliciano de Faria</span><span className="text-slate-500">Colaborador</span>
              <span className="font-semibold">Luiz Henrique Lima Veronesi</span><span className="text-slate-500">Criador e Desenvolvedor Principal da Plataforma; Colaborador DACILAT</span>
              <span className="font-semibold">Leonel de Alencar Araripe</span><span className="text-slate-500">Colaborador</span>
              <span className="font-semibold">Michael Becker</span><span className="text-slate-500">Colaborador</span>
              <span className="font-semibold">Vanda Pires</span><span className="text-slate-500">Colaborador</span>
              <span className="font-semibold">André Luiz Rosa Teixeira</span><span className="text-slate-500">Colaborador</span>
              <span className="font-semibold">Juliana Lopes Gurgel</span><span className="text-slate-500">Colaborador</span>
              <span className="font-semibold">Ticiana Andrade de Sena</span><span className="text-slate-500">Colaborador</span>
              <span className="font-semibold">Osmar Francisco</span><span className="text-slate-500">Colaborador</span>
              <span className="font-semibold">Hilário Silva</span><span className="text-slate-500">Colaborador</span>
              <span className="font-semibold">Sandra Silva</span><span className="text-slate-500">Colaborador</span>
            </div>
            <div className="pt-2">
              <a
                href="https://www.tycho.iel.unicamp.br/dacilat"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-indigo-600 hover:text-indigo-800 font-semibold transition-colors"
              >
                <span>Portal DACILAT</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          {/* Motor de busca complementar */}
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 space-y-1">
            <p className="text-[11px] text-slate-500">
              O <strong>Tycho Brahe Search</strong> (este motor de busca) foi elaborado por Gabriel Pinheiro como extensão e ferramenta complementar à Plataforma Tycho Brahe, com base em sua proposta de arquitetura cartográfica para a implementação de núcleos cartográficos.
            </p>
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
