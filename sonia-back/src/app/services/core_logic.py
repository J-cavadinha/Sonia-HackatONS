# src/core_logic.py (VERSÃO FINAL COM EXTRAÇÃO DE SLUGS EXPLÍCITOS)

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import os
import re
from typing import List, Tuple, Dict
from collections import defaultdict
from .json_retrieval import JSONDatasetRetriever
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

s3_client = boto3.client('s3', region_name='sa-east-1', config=Config(signature_version=UNSIGNED))
BUCKET_NAME = "ons-aws-prod-opendata"

# --- Modelos Pydantic para Relevância de Arquivos ---
class FileRelevance(BaseModel):
    file_uri: str = Field(description="URI do arquivo S3")
    relevance_score: float = Field(description="Pontuação de relevância de 0.0 a 1.0")
    reason: str = Field(description="Explicação breve do por que este arquivo é relevante")

class FileSelection(BaseModel):
    relevant_files: List[FileRelevance] = Field(description="Lista de arquivos relevantes com pontuações")

def find_actual_data_files(dataset_slug: str) -> List[str]:
    """Encontra os ficheiros de dados CSV/Parquet mais recentes para um dado dataset slug no S3."""
    try:
        prefix = f"dataset/{dataset_slug}/"
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
        
        if 'Contents' not in response:
            return []
        
        files = []
        for obj in response['Contents']:
            key = obj['Key']
            if (key.lower().endswith('.csv') or key.lower().endswith('.parquet')) and 'dicionario' not in key.lower():
                full_uri = f"s3://{BUCKET_NAME}/{key}"
                files.append(full_uri)
        
        return files
        
    except Exception as e:
        print(f"Erro ao listar arquivos S3 para {dataset_slug}: {e}")
        return []

def find_relevant_datasets(user_question: str) -> Tuple[List[str], List[str], int]:
    """Usa o JSON retriever para encontrar slugs e dossiês de datasets relevantes."""
    retriever = JSONDatasetRetriever()
    
    dataset_slugs, dataset_reasons, token_count = retriever.find_relevant_datasets(user_question)
    
    if not dataset_slugs:
        return [], [], token_count
    
    all_uris = []
    dossiers = []
    for slug in dataset_slugs:
        data_files = find_actual_data_files(slug)
        all_uris.extend(data_files)
    print(f"{all_uris}")
    return dataset_reasons, all_uris, token_count

def score_file_relevance(file_uris: List[str], user_question: str, max_files: int = 5) -> List[str]:
    if not file_uris or len(file_uris) <= max_files:
        return file_uris
    
    if len(file_uris) <= max_files:
        return file_uris
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    parser = JsonOutputParser(pydantic_object=FileSelection)
    
    file_info = []
    for uri in file_uris:
        filename = os.path.basename(uri)
        base_name = os.path.splitext(filename)[0]
        clean_name = re.sub(r'_\d{4}', '', base_name)
        file_info.append({ 'uri': uri, 'filename': filename, 'clean_name': clean_name })
    
    prompt = f"""
Você é um especialista em análise de dados do ONS. Sua tarefa é avaliar a relevância de arquivos de dados para responder à pergunta do usuário.
**Pergunta do Usuário:** "{user_question}"
**Arquivos Disponíveis:**
"""
    
    for i, file_data in enumerate(file_uris):
        filename = os.path.basename(file_data)
        clean_name = re.sub(r'_\d{4}', '', os.path.splitext(filename)[0])
        prompt += f"\n{i+1}. {filename} (nome base: {clean_name})"
    
    prompt += f"""
**Instruções:**
1. Analise a pergunta do usuário e os nomes dos arquivos disponíveis.
2. Retorne os {max_files} arquivos mais relevantes com pontuações de 0.0 a 1.0.
3. Para cada arquivo, forneça uma razão clara para a sua escolha.
**Formato de Resposta (JSON):**
{parser.get_format_instructions()}
Responda APENAS com o JSON válido, sem texto adicional.
"""
    
    try:
        response = llm.invoke(prompt)
        parsed_response = parser.parse(response.content)
        relevant_files = parsed_response.get("relevant_files", [])
        relevant_files.sort(key=lambda x: x.relevance_score, reverse=True)
        selected_uris = [file_data.file_uri for file_data in relevant_files[:max_files]]
        
        print(f"INFO: Selecionados {len(selected_uris)} arquivos mais relevantes de {len(file_uris)} disponíveis.")
        for file_data in relevant_files[:max_files]:
            print(f"  - {os.path.basename(file_data.file_uri)} (relevância: {file_data.relevance_score:.2f}): {file_data.reason}")
        
        return selected_uris
        
    except Exception as e:
        print(f"Erro ao pontuar relevância dos arquivos: {e}")
        print(f"AVISO: Usando seleção por ordem como fallback.")
        return file_uris[:max_files]

def select_latest_files(uri_list: List[str], max_files: int = None, user_question: str = None) -> List[str]:
    if not uri_list:
        return []
        
    uris_to_load = []
    grouped_uris = defaultdict(list)
    for uri in uri_list:
        base_name = re.sub(r'_\d{4}', '', os.path.splitext(os.path.basename(uri))[0])
        grouped_uris[base_name].append(uri)

    for base_name, uris in grouped_uris.items():
        if not uris: continue
        
        def extract_year_from_uri(uri):
            match = re.search(r'(\d{4})', uri)
            return int(match.group(1)) if match else 0

        latest_uri = max(uris, key=extract_year_from_uri)
        uris_to_load.append(latest_uri)

    unique_uris = sorted(list(set(uris_to_load)))
    
    if max_files is None:
        max_files = int(os.getenv('MAX_FILES_LIMIT', '15'))
    
    if user_question and len(unique_uris) > max_files:
        print(f"INFO: Aplicando seleção por relevância para escolher os {max_files} arquivos mais relevantes de {len(unique_uris)} disponíveis.")
        return score_file_relevance(unique_uris, user_question, max_files)
    
    if len(unique_uris) > max_files:
        print(f"INFO: Limitando de {len(unique_uris)} para {max_files} arquivos para evitar sobrecarga do modelo.")
        unique_uris = unique_uris[:max_files]
    
    return unique_uris

def load_df_from_s3(s3_uri: str) -> pd.DataFrame:
    storage_options = {'anon': True, 'client_kwargs': {'region_name': 'sa-east-1'}}
    file_name = os.path.basename(s3_uri)

    try:
        if s3_uri.lower().endswith('.csv'):
            print(f"INFO: A tentar carregar CSV {file_name} com delimitador ';'")
            df = pd.read_csv(s3_uri, storage_options=storage_options, delimiter=';', on_bad_lines='skip')
            
            if df.shape[1] == 1:
                print(f"AVISO: Delimitador ';' resultou em uma coluna para {file_name}. A tentar com ','.")
                df = pd.read_csv(s3_uri, storage_options=storage_options, delimiter=',', on_bad_lines='skip')

        elif s3_uri.lower().endswith('.parquet'):
            print(f"INFO: A carregar ficheiro Parquet {file_name}")
            df = pd.read_parquet(s3_uri, storage_options=storage_options)
        
        else:
            raise ValueError(f"Formato de ficheiro não suportado para {file_name}. Apenas .csv e .parquet são aceites.")

        print(f"INFO: Ficheiro {file_name} carregado com sucesso. Shape: {df.shape}")
        return df
        
    except Exception as e:
        raise ValueError(f"Não foi possível carregar o ficheiro {s3_uri}. Erro: {e}")

# --- NOVA FUNÇÃO ---
def extract_explicit_slugs(question: str, chat_history: List[Dict]) -> List[str]:
    """
    Usa um LLM para identificar se o usuário mencionou um ou mais 'slugs' de datasets
    explicitamente na pergunta ou no histórico.
    """
    if not question and not chat_history:
        return []

    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """Sua tarefa é identificar menções explícitas a nomes técnicos de datasets (conhecidos como 'slugs') na conversa. Slugs são nomes curtos, em formato de código, como 'carga_energia_di' ou 'geracao_usina_2_ho'.

Analise a conversa abaixo:
Histórico:
{chat_history}
Pergunta mais recente:
{question}

Instruções:
1.  Procure por palavras que se pareçam com slugs (letras minúsculas, sublinhados, sem espaços).
2.  Se encontrar um ou mais slugs, retorne-os em uma lista, separados por vírgulas. Ex: carga_energia_di,geracao_usina_2_ho
3.  Se nenhum slug explícito for mencionado, retorne a string "N/A".
4.  Não invente slugs. Retorne apenas os que foram explicitamente escritos pelo usuário.

Sua resposta deve ser APENAS a lista de slugs ou "N/A"."""),
        ("human", "Pergunta: {question}")
    ])
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = prompt_template | llm | StrOutputParser()
    
    try:
        response = chain.invoke({
            "chat_history": history_str,
            "question": question
        })
        
        if response and response.strip().upper() != "N/A":
            slugs = [slug.strip() for slug in response.split(',') if slug.strip()]
            print(f"-> Slugs explícitos encontrados: {slugs}")
            return slugs
        else:
            print("-> Nenhum slug explícito encontrado.")
            return []
    except Exception as e:
        print(f"AVISO: Erro ao extrair slugs explícitos. Procedendo com busca normal. Erro: {e}")
        return []