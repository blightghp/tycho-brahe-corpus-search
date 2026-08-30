# Interface de Usuário (React + Tailwind)

Bem-vindo à área de desenvolvimento do _Frontend_. A UI foi construída com um princípio: permitir ao pesquisador/linguista explorar árvores abstratas complexas com a mesma facilidade que usa uma busca web.

## Estrutura Visual e Componentes

- **`App.tsx`**: Contém o contêiner mestre e gerencia o Menu lateral de navegação. 
- **`SearchBar.tsx`**: Trata o estado de requisições de consulta ao banco. Componente desenhado pensando em validações (garantir que um pesquisador não passe uma busca sintática incorreta, como abrir chave `[` sem fechar `]`).
- **`TreeView.tsx`**: O cérebro de exibição! Utilizando SVG nativo via `react-d3-tree`, a aplicação recebe as chaves sujas da estrutura JSON original e processa em nós visuais cartográficos coloridos.
- **`HumanInTheLoop.tsx`**: O painel de Auditoria. Um fluxo onde o usuário decide aceitar ou rejeitar as modificações propostas pelo algoritmo. O React cuida para passar o estado de forma reativa.

## Créditos do Projeto Histórico
A Interface de usuário carrega a herança formal de dados do projeto **Tycho Brahe** original, da Universidade Estadual de Campinas (IEL). Como política fundamental da UI/UX, mantemos a intuição de visualização fiel aos pesquisadores veteranos e carregamos as devidas referências institucionais em links dispostos no aplicativo. (http://www.tycho.iel.unicamp.br/)

## Desenvolvimento Local
Para trabalhar em alterações puramente visuais, sem recompilar o `.exe` inteiro, suba a aplicação com:
```bash
npm run tauri dev
```
