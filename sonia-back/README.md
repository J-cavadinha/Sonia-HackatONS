# S.O.N.I.A Backend 🧠

## Arquitetura

O backend é estruturado como uma aplicação **FastAPI** modular:

*   **`src/app/main.py`**: O ponto de entrada da API. Lida com requisições HTTP, CORS e orquestra o fluxo de requisição de alto nível.
*   **`src/app/agents/`**: Contém as definições dos agentes baseados em LangChain.
    *   `TaskRouterAgent`: Classifica a intenção.
    *   `DataAnalysisAgent`: Escreve código Python para analisar DataFrames do Pandas.
    *   `ChartAnalysisAgent`: Especializado em preparar estruturas de dados para gráficos no frontend.
*   **`src/app/services/`**: Lógica de negócios.
    *   `json_retrieval.py`: Manuseio da busca semântica sobre os metadados dos datasets.
    *   `core_logic.py`: Utilitários para interações com S3, download e carregamento de arquivos.
*   **`scripts/ingest_data.py`**: Um script ETL autônomo que escaneia o S3, processa metadados usando LLMs e popula o Vector Store local.

## Tecnologias Chave
*   **FastAPI**: Framework web de alta performance.
*   **LangChain**: Framework para construir aplicações com LLMs.
*   **ChromaDB**: Banco de dados vetorial open-source para busca semântica.
*   **Pandas**: Para manipulação e análise de dados em memória.
*   **Boto3**: SDK AWS para Python.
