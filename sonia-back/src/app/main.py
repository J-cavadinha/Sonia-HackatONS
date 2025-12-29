# src/fastapi_app.py (código completo e atualizado)

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uvicorn
import os

from .services.core_logic import find_relevant_datasets, load_df_from_s3, select_latest_files
from .agents.agents import TaskRouterAgent, DataAnalysisAgent, ChartAnalysisAgent
from .services.json_retrieval import JSONDatasetRetriever

# --- NOVOS IMPORTS PARA MANTER CONTEXTO ---
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- Inicialização dos Agentes ---
router_agent = TaskRouterAgent()
analysis_agent = DataAnalysisAgent()
chart_agent = ChartAnalysisAgent()
metadata_retriever = JSONDatasetRetriever()

# --- Modelos Pydantic (sem alterações) ---
class Message(BaseModel):
    role: str = Field(..., description="'user' ou 'assistant'")
    content: str = Field(..., description="Conteúdo da mensagem")

class AnalysisRequest(BaseModel):
    question: str = Field(..., description="Pergunta do usuário em português")
    chat_history: Optional[List[Message]] = Field(default=[], description="Histórico da conversa")

class DatasetInfo(BaseModel):
    path: str = Field(..., description="S3 path do dataset")

class AnalysisResponse(BaseModel):
    response: str = Field(..., description="Resposta do LLM em português")
    chart: str = Field(default="False", description="Tipo de gráfico: False, pie, bar, scatter, line")
    datasets_consumed: List[DatasetInfo] = Field(..., description="Lista de datasets utilizados")
    data_points: Optional[Dict[str, Any]] = Field(default={}, description="Dados para gráfico")

app = FastAPI(
    title="ONS Multi-Agent Data Analysis API",
    description="API que utiliza múltiplos agentes para fornecer análises de dados do ONS.",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173", "https://sonia-grupo1-production.up.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- NOVA FUNÇÃO PARA CRIAR PERGUNTA AUTÔNOMA ---
def create_standalone_question(question: str, chat_history: List[Message]) -> str:
    """
    Reformuala a pergunta do usuário para ser autônoma, incorporando o contexto do histórico.
    """
    if not chat_history:
        return question

    history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in chat_history])
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """Dada a conversa abaixo e a pergunta de acompanhamento, reformule a pergunta de acompanhamento para ser uma pergunta autônoma, em português.
        Ela deve conter todo o contexto necessário para ser entendida sem o histórico.
        Histórico:
        {chat_history}"""),
        ("human", "Pergunta de Acompanhamento: {question}")
    ])
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = prompt_template | llm | StrOutputParser()
    
    try:
        response = chain.invoke({
            "chat_history": history_str,
            "question": question
        })
        print(f"-> Pergunta original: '{question}'")
        print(f"-> Pergunta re-escrita com contexto: '{response}'")
        return response
    except Exception as e:
        print(f"AVISO: Erro ao re-escrever a pergunta. Usando a original. Erro: {e}")
        return question

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    """
    Endpoint principal que orquestra os agentes para responder à pergunta.
    """
    try:
        # --- ETAPA 0: CRIAR PERGUNTA AUTÔNOMA PARA MANTER O CONTEXTO ---
        standalone_question = create_standalone_question(request.question, request.chat_history)

        # --- ETAPA 1: ROTEAMENTO DA TAREFA ---
        print(f"1. Roteando a pergunta: '{standalone_question}'")
        route = router_agent.route_question(standalone_question)
        task_type = route.get("task_type")
        print(f"-> Rota decidida: {task_type}. Razão: {route.get('reasoning')}")

        # --- LÓGICA DE EXECUÇÃO BASEADA NA ROTA ---

        if task_type == "metadata_search":
            print("2. Executando busca de metadados...")
            
            # Primeiro, verifica se a pergunta é sobre um dataset específico
            is_specific, dataset_slug = metadata_retriever.is_specific_dataset_question(standalone_question)
            
            if is_specific:
                print(f"-> Pergunta específica sobre dataset: {dataset_slug}")
                # Fornece informações detalhadas sobre o dataset específico
                response_text, token_count, used_datasets = metadata_retriever.get_detailed_dataset_info(
                    dataset_slug, standalone_question
                )
                dataset_paths = [DatasetInfo(path=f"dataset/{dataset_slug}/")]
            else:
                print("-> Pergunta ampla sobre metadados, buscando datasets relevantes...")
                # Busca datasets relevantes de forma ampla
                slugs, reasons, _ = metadata_retriever.find_relevant_datasets(standalone_question)
                
                if not slugs:
                    response_text = "Não encontrei datasets que correspondam à sua pergunta sobre metadados."
                    dataset_paths = []
                else:
                    response_text = "Encontrei os seguintes datasets que podem ser relevantes para a sua pergunta:\n"
                    for i, slug in enumerate(slugs):
                        response_text += f"\n- **{slug}**: {reasons[i]}"
                    
                    # Converte slugs em DatasetInfo para manter consistência
                    dataset_paths = [DatasetInfo(path=f"dataset/{slug}/") for slug in slugs]
            
            return AnalysisResponse(
                response=response_text,
                datasets_consumed=dataset_paths,
                data_points={}
            )

        # Rota 2: Pergunta simples que pode ser respondida via metadados
        elif task_type == "simple_question":
            print("2. Executando resposta de pergunta simples via metadados...")
            response_text, token_count, used_datasets = metadata_retriever.answer_simple_question(request.question)
            
            # Converte slugs em DatasetInfo para manter consistência
            dataset_paths = [DatasetInfo(path=f"dataset/{slug}/") for slug in used_datasets]
            
            return AnalysisResponse(
                response=response_text,
                datasets_consumed=dataset_paths,
                data_points={}
            )

        # Rota 3, 4 e 5: Análise Simples, Complexa ou de Gráficos (requerem carregamento de dados)
        elif task_type in ["simple_analysis", "complex_analysis", "chart_analysis"]:
            # --- ETAPA 2: BUSCA E CARREGAMENTO DE DADOS ---
            print("2. Buscando datasets relevantes...")
            dossiers, all_uris, _ = find_relevant_datasets(standalone_question) # <- USA PERGUNTA COM CONTEXTO
            
            if not all_uris:
                raise HTTPException(status_code=404, detail="Nenhum dataset relevante encontrado para a análise.")
            
            combined_dossier = "\n\n---\n\n".join(dossiers)
            max_files = int(os.getenv('MAX_FILES_LIMIT', '15'))
            uris_to_load = select_latest_files(all_uris, max_files=max_files, user_question=standalone_question)
            
            print(f"3. Carregando {len(uris_to_load)} ficheiro(s) de dados do S3...")
            loaded_dfs = []
            for uri in uris_to_load:
                try:
                    df = load_df_from_s3(uri)
                    df.name = os.path.basename(uri).replace('.csv', '')
                    loaded_dfs.append(df)
                except Exception as e:
                    print(f"AVISO: Não foi possível carregar o ficheiro {uri}. Erro: {e}")
                    continue
            
            if not loaded_dfs:
                raise HTTPException(status_code=500, detail="Os datasets relevantes foram encontrados, mas não puderam ser carregados.")

            # --- ETAPA 3: EXECUÇÃO DA ANÁLISE ---
            if task_type == "chart_analysis":
                print("4. Executando a análise de gráficos com o agente especialista...")
                analysis_result = chart_agent.run_chart_analysis(
                    dfs=loaded_dfs,
                    user_question=standalone_question, # <- USA PERGUNTA COM CONTEXTO
                    dossier=combined_dossier
                )
            else:
                print("4. Executando a análise de dados com o agente especialista...")
                analysis_result = analysis_agent.run_analysis(
                    dfs=loaded_dfs,
                    user_question=standalone_question, # <- USA PERGUNTA COM CONTEXTO
                    dossier=combined_dossier
                )
                analysis_result['chart'] = 'False'
                analysis_result['data_points'] = {}
            
            # --- ETAPA 4: FORMATAÇÃO DA RESPOSTA FINAL ---
            print("5. Análise concluída. A formatar a resposta.")
            dataset_paths = [DatasetInfo(path=uri.replace('/' + os.path.basename(uri), '/')) for uri in uris_to_load]

            return AnalysisResponse(
                response=analysis_result['output'],
                chart=analysis_result.get('chart', 'False'),
                datasets_consumed=dataset_paths,
                data_points=analysis_result.get('data_points', {})
            )
            
        else:
            raise HTTPException(status_code=500, detail=f"Tipo de tarefa desconhecido: {task_type}")

    except Exception as e:
        print(f"Erro fatal no endpoint /analyze: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno no servidor: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("src.app.main:app", host="0.0.0.0", port=8000, reload=True)