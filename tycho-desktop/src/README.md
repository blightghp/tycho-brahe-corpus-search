# Interface de Usuário (React + Tailwind + D3)

O frontend do Tycho Brahe Desktop foi concebido com rigor visual e metodológico para permitir a linguistas, pesquisadores e estudantes explorarem árvores sintáticas profundas e a hierarquia cartográfica em 5 Grandes Domínios.

## Componentes Principais

- **`App.tsx`**: Contêiner mestre da aplicação, com navegação fluida em abas (*Pesquisa em Árvores*, *Quarentena/Auditoria*, *Status do Sistema*), monitoramento de saúde do motor Rust e cabeçalho institucional com links para a UNICAMP.
- **`SearchBar.tsx`**: Barra de consulta com verificação em tempo real de balanceamento de colchetes sintáticos e chips de filtro rápido para os 5 Domínios Gerativos (`D1: VocP`, `D2: ForceP`, `D3: MoodP_eval`, `D3: T_anterior`, `D4: FocP_low`, `D5: VoiceP_agent`, `D5: ApplP_low`, `D5: Root`).
- **`TreeView.tsx`**: Visualizador hierárquico SVG interativo com pan e zoom dinâmico baseado em `react-d3-tree`. Utiliza uma paleta cromática padronizada para os 5 Domínios Cartográficos:
  - 🟣 **D1 (Ato de Fala)**: Violeta (`#8b5cf6`)
  - 🔵 **D2 (Split-CP)**: Índigo / Azul (`#3b82f6`)
  - 🟢 **D3 (Split-IP / Cinque)**: Esmeralda / Verde (`#10b981`)
  - 🟠 **D4 (Baixa Periferia)**: Âmbar / Laranja (`#f59e0b`)
  - 🔴 **D5 (Split-vP / First Phase)**: Rosa / Carmim (`#f43f5e`)
  - ⚪ **Constituintes Canônicos**: Cinza / Ardósia (`#64748b`)
- **`TermBreakdown.tsx`**: Grade analítica termo a termo que exibe cada palavra da sentença com seu lema spaCy, classe gramatical (POS), domínio gerativo, projeção correspondente e papel funcional.
- **`HumanInTheLoop.tsx`**: Painel de curadoria e auditoria supervisionada para resolução de quarentenas e sentenças anômalas.
- **`CreditsModal.tsx`**: Modal com atribuições formais, links oficiais ao portal da UNICAMP (http://www.tycho.iel.unicamp.br/) e referências bibliográficas fundamentais (Rizzi 1997, Cinque 1999, Belletti 2004, Ramchand 2008, Speas & Tenny 2003).

## Desenvolvimento Local
Para executar em modo de desenvolvimento com hot-reload:
```bash
npm run tauri dev
```
