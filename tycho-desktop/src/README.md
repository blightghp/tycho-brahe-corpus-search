# Interface de Usuário (React + Tailwind + D3)

O frontend do Tycho Brahe Desktop foi concebido com rigor visual e metodológico para permitir a linguistas, pesquisadores e estudantes explorarem árvores sintáticas profundas e a hierarquia cartográfica em 5 Grandes Domínios.

> [!WARNING]
> A interface é experimental. A presença de chips, cores e componentes para os
> cinco domínios não comprova que a busca, os bancos ou a persistência de
> auditoria estejam validados. Veja
> [`../../docs/STATUS_DE_ARTEFATOS.md`](../../docs/STATUS_DE_ARTEFATOS.md).

## Componentes Principais

- **`App.tsx`**: Contêiner mestre da aplicação, com a rota **Busca Evidencial (M4)**, a consulta histórica preservada para auditoria, quarentena, status do sistema e cabeçalho institucional com links para a UNICAMP.
- **`M4SearchPanel.tsx`**: Formulário tipado de busca por entidade, rótulo, projeção, token ou regra. Exibe origem, âncora, decisão e evidências sem transformar classificações pendentes em confirmação científica.
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
- **`CreditsModal.tsx`**: Modal com direitos reservados à Plataforma Tycho Brahe © 2026, atribuição de criação e desenvolvimento principal a Luiz Henrique Lima Veronesi, orientação da Professora Dra. Charlotte Galves (IEL/UNICAMP), referência à tese, participantes do DACILAT e links oficiais HTTPS.

A rota M4 exige sidecar dedicado e um SQLite Marco 3 validado no diretório
controlado da aplicação. As instruções de build, provisionamento e limites
estão em [`../../docs/INTEGRACAO_DESKTOP_M4.md`](../../docs/INTEGRACAO_DESKTOP_M4.md).

## Desenvolvimento Local
Para executar em modo de desenvolvimento com hot-reload:
```bash
npm run tauri dev
```
