# src/agents.py (código completo com prompts aprimorados)

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from typing import List, Dict, Literal, Tuple
from langchain_openai import ChatOpenAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# TaskRouterAgent e TaskRoute permanecem inalterados
class TaskRoute(BaseModel):
    task_type: Literal["metadata_search", "simple_question", "simple_analysis", "complex_analysis", "chart_analysis"] = Field(description="O tipo de tarefa a ser executada com base no prompt do usuário.")
    reasoning: str = Field(description="Breve explicação do porquê esta rota foi escolhida.")

class TaskRouterAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.parser = JsonOutputParser(pydantic_object=TaskRoute)

    def route_question(self, user_question: str) -> Dict:
        prompt = f"""
Você é um especialista em roteamento de tarefas de análise de dados. Sua função é analisar a pergunta de um usuário e decidir qual tipo de agente é mais adequado para respondê-la. SEMPRE responda em PORTUGUÊS BRASILEIRO.

**Categorias de Tarefa:**
- `metadata_search`: Use esta categoria para perguntas sobre os datasets em si, como "Quais dados você tem sobre X?", "Qual dataset fala sobre Y?", "Quais campos tem o dataset Z?", "Me explique o dataset ABC". Estas perguntas não requerem a leitura dos dados do ficheiro, apenas dos metadados.
- `simple_question`: Use para perguntas que podem ser respondidas diretamente através dos títulos e descrições dos datasets, sem precisar carregar os dados reais. Ex: "O que é geração por usina?", "Como funciona o sistema de intercâmbio?", "O que significa TEIFa?". Estas perguntas são conceituais e podem ser respondidas com base nas descrições dos metadados.
- `simple_analysis`: Use para perguntas que envolvem um cálculo direto ou um filtro simples em um único conjunto de dados. Ex: "Qual é a capacidade total de geração?", "Liste as usinas do tipo X.".
- `complex_analysis`: Use para perguntas que requerem múltiplos passos, comparações entre categorias, agregações complexas ou o uso de múltiplos datasets. Ex: "Compare a geração X com a Y no subsistema Z.", "Qual foi a evolução mensal do indicador X?".
- `chart_analysis`: Use para perguntas que explicitamente pedem visualizações, gráficos ou representações visuais dos dados. Ex: "Mostre um gráfico de barras da geração por usina", "Crie um gráfico de pizza da distribuição por subsistema", "Faça um gráfico de linha da evolução temporal".

**Pergunta do Usuário:**
"{user_question}"

**Instruções:**
1. Analise a pergunta.
2. Escolha a categoria de tarefa mais apropriada.
3. Forneça uma breve justificação para a sua escolha.

**Formato de Resposta (JSON):**
{self.parser.get_format_instructions()}

Responda APENAS com o JSON válido.
"""
        try:
            response = self.llm.invoke(prompt)
            parsed_response = self.parser.parse(response.content)
            return parsed_response
        except Exception as e:
            print(f"Erro ao rotear a pergunta: {e}")
            return {"task_type": "complex_analysis", "reasoning": "Fallback devido a erro de roteamento."}

class DataAnalysisAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)

    def run_analysis(self, dfs: List[pd.DataFrame], user_question: str, dossier: str) -> Dict:
        if not dfs:
            return {'output': "Nenhum dado foi carregado para análise. Verifique os passos anteriores.", 'intermediate_steps': []}

        df_name_mapping = {f'df{i+1}': getattr(df, 'name', f'ficheiro_{i+1}') for i, df in enumerate(dfs)}
        df_name_str = "\n".join([f"- `{k}`: Corresponde ao conjunto de dados '{v}'" for k, v in df_name_mapping.items()])

        # --- PROMPT ATUALIZADO E REFORÇADO DO AGENTE ANALISTA ---
        AGENT_PREFIX = f"""Você é um analista de dados sênior do ONS, com a responsabilidade de ser extremamente preciso e literal. Sua credibilidade depende de nunca responder a uma pergunta usando dados incorretos. SEMPRE responda em PORTUGUÊS BRASILEIRO.

**Contexto da Análise:**
- **Pergunta Autônoma com Contexto:** "{user_question}"
- **Dossiê dos Dados (Resumo dos datasets encontrados):**
{dossier}
- **DataFrames Carregados para Análise:**
{df_name_str}

**FLUXO DE TRABALHO CRÍTICO E OBRIGATÓRIO:**

**1. Planejamento (Thought Process):**
<<<<<<< HEAD
Antes de escrever qualquer código, detalhe o seu plano de análise passo a passo. O seu plano DEVE incluir:
   a. **Validação dos Dados:** O seu primeiro passo é SEMPRE verificar a integridade dos DataFrames (`df.info()`, `df.head()`). Se os dados parecerem mal formatados, pare e reporte o erro.
   b. **LIMITES DE TOKENS - CRÍTICO:** Datasets podem ter milhares de linhas. SEMPRE filtre os dados ANTES de processá-los:
      - Se a pergunta menciona um ANO específico (ex: "2024", "este ano"), filtre APENAS esse ano
      - Se a pergunta pede "últimos 3 anos" mas há milhares de linhas, limite a um período menor (último ano ou últimos meses)
      - Se a pergunta pede "dados recentes" ou "últimos dados", use `.tail()` ou filtre pela data mais recente
      - Se não há filtro temporal na pergunta mas o dataset é muito grande (>1000 linhas), AVISE o usuário e mostre apenas uma AMOSTRA representativa (ex: últimos 100 registros, ou agregação por período)
      - NUNCA tente processar datasets completos com milhares de linhas - você excederá os limites de tokens
   c. **Seleção de Dados e Coerência:** Identifique EXATAMENTE qual DataFrame e quais colunas você usará. Justifique a sua escolha. **REGRA CRÍTICA:** Se a pergunta envolve uma comparação (ex: comparar A e B), você DEVE usar a mesma métrica e os mesmos DataFrames base para ambas as partes da comparação. Não use o dataset de 'carga' para uma parte e o de 'geração' para outra, a menos que o usuário peça explicitamente. Seja consistente.
   d. **Passos da Análise:** Liste as operações (filtros, agregações, cálculos) que irá executar.
   e. **Pesquisa de Nomes** Quando passado um nome em uma busca (ex: "Usina X"), use sempre correspondência parcial ou regex, garantindo que ache o dado.
   f. **Verificação Final:** Confirme que o seu plano aborda TODAS as partes da pergunta do usuário de forma coerente.
=======
Antes de escrever qualquer código, detalhe o seu plano. O plano DEVE seguir estes passos na ordem exata:

   **a. Verificação de Relevância (Passo Mais Importante):**
   - **Objetivo:** Confirmar se os DataFrames carregados são PERFEITAMENTE adequados para responder à "Pergunta Autônoma com Contexto".
   - **Ação:** Inspecione os nomes dos DataFrames (`df_name_str`) e as primeiras linhas de cada um (`df.head()`). Compare as colunas e os valores com os termos-chave da pergunta.
   - **REGRA DE OURO:** Se a pergunta é sobre "carga de energia por subsistema" e os DataFrames contêm colunas como `val_ciper1` ou nomes como `interrupcao_carga`, eles são IRRELEVANTES.
   - **SE OS DADOS FOREM IRRELEVANTES:** Sua tarefa TERMINA AQUI. Sua resposta final DEVE ser uma mensagem clara informando a discrepância. Exemplo de resposta final: "Não foi possível responder. Os datasets carregados (`nome_do_df_errado`) parecem conter dados sobre 'carga interrompida', mas a pergunta era sobre 'carga de energia por subsistema'. Por favor, reformule a pergunta para garantir que os datasets corretos sejam encontrados."
   - **NUNCA, JAMAIS, prossiga com a análise se os dados não corresponderem EXATAMENTE à pergunta.**

   **b. Validação de Integridade:**
   - Apenas se os dados forem relevantes, verifique a integridade (`df.info()`).

   **c. Estratégia de Filtragem (Controle de Custos e Otimização):**
   - ANTES DE QUALQUER PROCESSAMENTO, identifique filtros críticos baseados na pergunta para usar sempre o menor subconjunto possível dos dados

   **d. Passos da Análise:**
   - Detalhe as operações (filtros, agregações, cálculos) que você executará nos dados já validados e pré-filtrados.


**2. Execução:**
Execute o seu plano passo a passo usando `python_repl_ast`.

**3. Resposta Final:**
Formule uma resposta final clara e direta, baseada exclusivamente nos resultados da sua análise.

Comece agora, seguindo estritamente este fluxo de trabalho. Sua primeira ação é a **Verificação de Relevância**.
"""
        
        agent = create_pandas_dataframe_agent(
            llm=self.llm,
            df=dfs,
            prefix=AGENT_PREFIX,
            verbose=True,
            agent_executor_kwargs={"handle_parsing_errors": True},
            allow_dangerous_code=True,
            return_intermediate_steps=True,
            max_iterations=8
        )
        
        try:
            response = agent.invoke({"input": user_question})
            
            final_output = response.get('output', 'Não foi possível obter uma resposta.')
            if "Agent stopped" in final_output:
                final_output = "A análise foi interrompida pois a tarefa é muito complexa ou encontrou um erro. Tente reformular a pergunta de forma mais simples."

            return {
                'output': final_output,
                'intermediate_steps': response.get('intermediate_steps', [])
            }

        except Exception as e:
            print(f"Erro durante a execução do agente de análise: {e}")
            error_message = (
                "Ocorreu um erro inesperado durante a análise dos dados. "
                "Isso pode ter acontecido porque a pergunta é muito complexa ou os dados não são adequados para a tarefa. "
                "Tente simplificar ou reformular sua pergunta."
            )
            return {'output': error_message, 'intermediate_steps': []}

# O ChartAnalysisAgent permanece inalterado, pois sua lógica já é bem específica.
class ChartAnalysisAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)

    def run_chart_analysis(self, dfs: List[pd.DataFrame], user_question: str, dossier: str) -> Dict:
        if not dfs:
            return {'output': "Nenhum dado foi carregado para análise. Verifique os passos anteriores.", 'chart': 'False', 'data_points': {}}

        df_name_mapping = {f'df{i+1}': getattr(df, 'name', f'ficheiro_{i+1}') for i, df in enumerate(dfs)}
        df_name_str = "\n".join([f"- `{k}`: Corresponde ao conjunto de dados '{v}'" for k, v in df_name_mapping.items()])

        CHART_AGENT_PREFIX = f"""Você é um analista de dados especializado em visualizações do ONS. Use a arquitetura ReAct para criar gráficos baseados nos dados fornecidos.

**Contexto da Análise:**
- **Pergunta do Usuário:** {user_question}
- **Dossiê dos Dados (Resumo):**
{dossier}
- **DataFrames Carregados:**
{df_name_str}

**TIPOS DE GRÁFICO SUPORTADOS:**
- `bar`: Gráfico de barras (comparação entre categorias)
- `pie`: Gráfico de pizza (distribuição percentual)
- `line`: Gráfico de linha (evolução temporal ou sequencial)

**ARQUITETURA ReAct - SIGA ESTE FLUXO:**

**Thought (Pensamento):**
Analise os padrões nos dados e identifique:
- Qual tipo de gráfico é mais adequado
- Quais colunas e dados usar
- Como agregar ou filtrar os dados
- Qual será o título e quais serão as categorias

**CRÍTICO - LIMITES DE TOKENS e TEMPO:**
- ANTES DE QUALQUER PROCESSAMENTO, identifique filtros críticos baseados na pergunta para usar sempre o menor subconjunto possível dos dados.
- Limite a no máximo 20-30 categorias/pontos para gráficos.

**Action (Ação):**
Execute o código Python usando `python_repl_ast` para extrair e processar os dados.

**Observation (Observação):**
Interprete os dados obtidos.

**Final Answer (Resposta Final):**
Dentro do Final Answer, forneça TUDO junto:
PRIMEIRO: Uma breve interpretação textual em português.
DEPOIS: Os dados estruturados no formato exato especificado para `bar`, `pie`, ou `line`.

**REGRAS CRÍTICAS:**
- SEMPRE responda em PORTUGUÊS BRASILEIRO
- NUNCA use bibliotecas de visualização (matplotlib, etc.)
- Os data points devem estar no formato exato especificado.

Comece agora com Thought.
"""
        
        agent = create_pandas_dataframe_agent(
            llm=self.llm,
            df=dfs,
            prefix=CHART_AGENT_PREFIX,
            verbose=True,
            agent_executor_kwargs={"handle_parsing_errors": "A formatação da sua resposta para o gráfico está incorreta, por favor corrija e tente novamente."},
            allow_dangerous_code=True,
            return_intermediate_steps=True,
            max_iterations=5
        )
        
        try:
            response = agent.invoke({"input": user_question})
            final_output = response.get('output', 'Não foi possível obter uma resposta.')
            
            if "Agent stopped" in final_output or "Invalid Format" in final_output:
                final_output = "A análise foi interrompida devido a um erro de formato. Tente reformular a pergunta de forma mais simples."

            chart_type, data_points, clean_output = self._extract_chart_info(final_output)
            
            return {
                'output': clean_output if clean_output.strip() else final_output,
                'chart': chart_type,
                'data_points': data_points,
                'intermediate_steps': response.get('intermediate_steps', [])
            }

        except Exception as e:
            print(f"Erro durante a execução do agente de gráficos: {e}")
            error_message = (
                "Ocorreu um erro ao tentar gerar o gráfico. "
                "Isso pode ter acontecido porque a pergunta é muito complexa ou os dados não são adequados para visualização. "
                "Tente simplificar a sua pergunta."
            )
            return {
                'output': error_message,
                'chart': 'False',
                'data_points': {},
                'intermediate_steps': []
            }

    def _extract_chart_info(self, output: str) -> Tuple[str, Dict, str]:
        import re
        import json
        
        chart_type = 'False'
        data_points = {}
        clean_lines = []
        is_json_block = False
        json_str_lines = []

        try:
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_str = output[json_start:json_end]
                text_output = output[:json_start].strip()
                
                parsed_json = json.loads(json_str)
                
                if 'chart_type' in parsed_json and 'data_points' in parsed_json:
                    chart_type = parsed_json.get('chart_type', 'False')
                    data_points = parsed_json.get('data_points', {})
                    return chart_type, data_points, text_output
        except (json.JSONDecodeError, IndexError) as e:
            print(f"AVISO: Não foi possível extrair o JSON do output do agente de gráfico. Erro: {e}")

        for line in output.split('\n'):
            if line.strip().startswith('{'):
                is_json_block = True
            
            if not is_json_block:
                clean_lines.append(line)
            else:
                json_str_lines.append(line)
                
            if line.strip().endswith('}'):
                is_json_block = False
        
        clean_output = '\n'.join(clean_lines).strip()
        
        if json_str_lines:
            try:
                full_json_str = "".join(json_str_lines)
                parsed_json = json.loads(full_json_str)
                chart_type = parsed_json.get('chart_type', 'False')
                data_points = parsed_json.get('data_points', {})
            except json.JSONDecodeError:
                return 'False', {}, output
        
        return chart_type, data_points, clean_output