# src/analysis_agent.py

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from typing import List, Dict, Tuple
from langchain_openai import ChatOpenAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_community.callbacks import get_openai_callback
from langchain_core.agents import AgentAction

def summarize_conversation(chat_history: List[Dict]) -> tuple[str, int]:
    if not chat_history: return "Não há histórico de conversa.", 0
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    
    summarizer_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    prompt = f"Resuma a seguinte conversa de forma concisa: {history_str}"
    
    with get_openai_callback() as cb:
        summary = summarizer_llm.invoke(prompt).content
        token_count = cb.total_tokens
    return summary, token_count

def extract_chart_info(agent_response: str) -> Tuple[str, List[Dict]]:
    """
    Extrai informações sobre gráficos da resposta do agente.
    """
    return "False", []

def run_multi_df_analysis(dfs: List[pd.DataFrame], user_question: str, chat_history: List[Dict], dossier: str):
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    # O agente irá referir-se aos dataframes como df1, df2, etc.
    # Criamos um mapeamento para mostrar os nomes originais.
    df_name_mapping = {f'df{i+1}': getattr(df, 'name', f'ficheiro_{i+1}') for i, df in enumerate(dfs)}
    df_name_str = "\n".join([f"- `{k}`: Corresponde ao conjunto de dados '{v}'" for k, v in df_name_mapping.items()])

    conversation_summary, summarizer_tokens = summarize_conversation(chat_history)

    AGENT_PREFIX = f"""Você é um analista de dados especialista.

CONTEXTO:
- Dossiê dos dados (resumo dos ficheiros): 
{dossier}
- DataFrames carregados: {len(dfs)} dataframes foram carregados.
- Pergunta: {user_question}

INSTRUÇÕES IMPORTANTES:
1.  **Acesso aos Dados**: Os dataframes estão disponíveis como `df1`, `df2`, etc. Use estas variáveis para aceder aos dados no seu código python. A correspondência é a seguinte:
{df_name_str}
2.  **Exemplo**: Para ver as primeiras linhas do primeiro dataframe, o seu código deve ser `print(df1.head())`.
3.  **Ferramentas**: Use apenas a ferramenta `python_repl_ast` para executar código pandas.
4.  **Saída Simples**: NÃO gere estruturas complexas como dicionários ou listas na sua resposta final.
5.  **Foco em Texto**: NÃO tente criar gráficos ou visualizações. Forneça apenas interpretações e resultados em texto.
6.  **Idioma**: Responda sempre em português do Brasil.
7.  **Conciso e Direto**: Mantenha as suas respostas e pensamentos concisos. Se o ficheiro CSV tiver o cabeçalho na primeira linha e os dados separados por ';', trate isso primeiro.

Comece agora.
"""
    
    agent = create_pandas_dataframe_agent(
        llm, dfs, prefix=AGENT_PREFIX, verbose=True,
        agent_executor_kwargs={"handle_parsing_errors": True},
        allow_dangerous_code=True, return_intermediate_steps=True, max_iterations=7
    )
    
    with get_openai_callback() as cb:
        response = agent.invoke({"input": user_question})
        agent_tokens = cb.total_tokens

    # DEBUG: Mostrar reasoning detalhado
    print("\n" + "="*50)
    print("🔍 DEBUG - REASONING DO GPT-4o")
    print("="*50)
    
    # LOOP DE DEBUG ROBUSTO
    if 'intermediate_steps' in response and isinstance(response['intermediate_steps'], list):
        print(f"📊 Número de passos: {len(response['intermediate_steps'])}")
        for i, step in enumerate(response['intermediate_steps']):
            print(f"\n--- PASSO {i+1} ---")
            if isinstance(step, tuple) and len(step) > 0 and isinstance(step[0], AgentAction):
                action = step[0]
                observation = step[1] if len(step) > 1 else "N/A"
                print(f"💭 Pensamento: {action.log.split('Action:')[0].strip()}")
                print(f"🎯 Ação: {action.tool}")
                print(f"🛠️ Input da Ação:\n{action.tool_input}")
                print(f"👁️ Observação: {str(observation)[:500]}...")
            else:
                print(f"⚠️ Passo malformado: {step}")
    else:
        print("❌ Nenhum passo intermediário encontrado ou formato inesperado")
    
    print(f"\n📝 OUTPUT FINAL:")
    final_output = response.get('output', 'Sem output')
    if "Agent stopped" in final_output:
        final_output = "A sua pergunta é muito complexa ou encontrei um erro. Por favor, tente reformular de forma mais simples."
    print(final_output)
    
    print(f"\n🔢 TOKENS: {agent_tokens}")
    print("="*50)

    total_tokens = summarizer_tokens + agent_tokens
    
    # Construir o objeto de resposta final
    final_response = {
        'output': final_output,
        'total_tokens': total_tokens
    }
    
    chart_type, data_points = extract_chart_info(final_output)
    final_response['chart_type'] = chart_type
    final_response['data_points'] = data_points
    
    return final_response