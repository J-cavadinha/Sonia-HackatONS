# S.O.N.I.A Frontend 💻

A interface moderna e responsiva para a plataforma S.O.N.I.A, construída com **React** e **Vite**.

## Funcionalidades

*   **Interface de Chat**: Uma UI familiar baseada em chat para interações naturais.
*   **Renderização Dinâmica de Componentes**: O chat suporta a renderização não apenas de texto, mas de visualizações interativas (Chart.js) diretamente no fluxo da conversa.
*   **Transparência da Fonte**: Uma barra lateral retrátil exibe os datasets específicos (CSVs/Parquets) usados para gerar cada resposta.
*   **Design Responsivo**: Otimizado para diversos tamanhos de tela.

## Estrutura do Projeto

*   **`src/components/`**: Componentes de UI reutilizáveis.
    *   `ChatCentral.tsx`: A lógica central do chat e gerenciamento de estado.
    *   `Barchart.tsx`, `Linechart.tsx`, etc.: Wrappers em torno de Recharts/Chart.js.
*   **`src/services/`**: Integração com API.
    *   `api.js`: Configuração centralizada do Axios para comunicação com o backend.

## Executando Localmente

1.  `npm install`
2.  `npm run dev`

O aplicativo estará disponível em `http://localhost:5173`.
