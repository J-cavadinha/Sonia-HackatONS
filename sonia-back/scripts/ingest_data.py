# src/index.py (código completo e corrigido)

from dotenv import load_dotenv
load_dotenv()

import os
import re
import boto3
import pandas as pd
import time
from collections import defaultdict
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError
from langchain.schema.document import Document
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import concurrent.futures
from openai import RateLimitError
from tenacity import retry, stop_after_attempt, wait_random_exponential

BUCKET_NAME = "ons-aws-prod-opendata"
REGION_NAME = "sa-east-1"
DB_PATH = "vector_store_db"
MAX_WORKERS = 5

s3_client = boto3.client('s3', region_name=REGION_NAME, config=Config(signature_version=UNSIGNED))
embedding_function = OpenAIEmbeddings(model="text-embedding-3-small")
llm = ChatOpenAI(model="gpt-4o", temperature=0)
temp_dir = "temp_download"
os.makedirs(temp_dir, exist_ok=True)

def get_dictionary_content(folder_prefix):
    try:
        files_in_folder = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=folder_prefix)['Contents']
    except KeyError:
        return None, "Pasta vazia ou sem acesso."
    
    dict_keys = defaultdict(list)
    for obj in files_in_folder:
        key = obj['Key']
        if 'dicionario' in key.lower():
            if key.lower().endswith('.json'): dict_keys['json'].append(key)
            elif key.lower().endswith('.csv'): dict_keys['csv'].append(key)
            elif key.lower().endswith('.pdf'): dict_keys['pdf'].append(key)
            
    chosen_key = None
    if dict_keys['json']: chosen_key = dict_keys['json'][0]
    elif dict_keys['csv']: chosen_key = dict_keys['csv'][0]
    elif dict_keys['pdf']: chosen_key = dict_keys['pdf'][0]
    
    if not chosen_key: return None, "Nenhum dicionário de dados (json, csv, pdf) encontrado."

    local_path = os.path.join(temp_dir, os.path.basename(chosen_key) + f"_{os.getpid()}_{int(time.time())}")

    try:
        s3_client.download_file(BUCKET_NAME, chosen_key, local_path)
    except ClientError as e:
        return None, f"Erro Boto3 ao descarregar {chosen_key}: {e}"

    content = ""
    try:
        if chosen_key.lower().endswith('.pdf'):
            content = " ".join(page.page_content for page in PyMuPDFLoader(local_path).load())
        elif chosen_key.lower().endswith('.json'):
            content = pd.read_json(local_path).to_string()
        elif chosen_key.lower().endswith('.csv'):
            content = pd.read_csv(local_path, sep=';', encoding='latin-1').to_string()
        os.remove(local_path)
        return content, None
    except Exception as e:
        if os.path.exists(local_path): os.remove(local_path)
        return None, f"Erro ao ler o dicionário {chosen_key}: {e}"

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def invoke_llm_with_retry(prompt):
    return llm.invoke(prompt)

def process_folder(folder_prefix):
    print(f"Analisando: {folder_prefix}")
    
    dict_content, error = get_dictionary_content(folder_prefix)
    if error:
        print(f" -> AVISO em '{folder_prefix}': {error}")
        return None

    data_files = defaultdict(dict)
    years = set()
    for obj in s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=folder_prefix).get('Contents', []):
        key = obj['Key']
        if 'dicionario' not in key.lower() and (key.lower().endswith('.csv') or key.lower().endswith('.parquet')):
            base_name = os.path.splitext(os.path.basename(key))[0]
            uri = f"s3://{BUCKET_NAME}/{key}"
            
            if key.lower().endswith('.parquet'):
                data_files[base_name]['parquet'] = uri
            elif key.lower().endswith('.csv'):
                data_files[base_name]['csv'] = uri
            
            if year_match := re.search(r'(\d{4})', key):
                years.add(int(year_match.group(1)))

    final_uris = [v.get('parquet', v.get('csv')) for v in data_files.values()]
    if not final_uris:
        print(f" -> AVISO em '{folder_prefix}': Nenhum ficheiro de dados encontrado.")
        return None
        
    temporal_scope = f"Dados de {min(years)} a {max(years)}." if years else "Escopo temporal não identificado."

    try:
        dossier_generation_prompt = f"""
        Você é um especialista em catalogação de dados do Operador Nacional do Sistema Elétrico (ONS).
        Sua tarefa é criar um resumo técnico (um "dossiê") para um conjunto de dados, com base no seu dicionário de dados e metadados.

        **Dicionário de Dados Fornecido:**
        ---
        {dict_content}
        ---

        **Metadados Adicionais:**
        - Nome da Pasta: {folder_prefix}
        - Período dos Dados: {temporal_scope}

        **Instruções para a Geração do Dossiê:**
        1.  **Título do Conjunto:** Crie um título claro e conciso que descreva o propósito principal do conjunto de dados. Ex: "Capacidade de Geração de Usinas Hidrelétricas por Subsistema".
        2.  **Resumo Detalhado:** Escreva um parágrafo explicando que tipo de informação este conjunto de dados contém. Mencione as principais métricas e dimensões (ex: "Contém a capacidade instalada em MW para cada usina, com informações de localização por estado e subsistema").
        3.  **Entidades-Chave e Tópicos:** Liste as palavras-chave e tópicos mais importantes. Estas palavras serão usadas para encontrar este conjunto de dados. Inclua sinónimos e termos técnicos. (ex: Geração de energia, usinas, hidrelétricas, capacidade instalada, potência, MW, subsistema, Sudeste, Nordeste, Itaipu, Belo Monte, etc.).
        4.  **Escopo Temporal:** Indique claramente o período coberto pelos dados.

        **Formato de Saída (Use exatamente este formato):**
        Título do Conjunto: [Seu título aqui]
        Resumo: [Seu resumo aqui]
        Tópicos Principais: [Suas palavras-chave aqui, separadas por vírgula]
        Período: [Período dos dados aqui]
        """
        
        generated_dossier = invoke_llm_with_retry(dossier_generation_prompt).content
        
        # --- CORREÇÃO: Converter a lista de URIs numa única string ---
        # ChromaDB não suporta listas nos metadados, então juntamos as URIs com "\n".
        sources_as_string = "\n".join(final_uris)
        new_doc = Document(page_content=generated_dossier, metadata={"sources": sources_as_string})
        
        print(f" -> OK! '{folder_prefix}' processado com {len(final_uris)} ficheiros.")
        return new_doc

    except RateLimitError as e:
        print(f" -> ERRO FATAL de Rate Limit em '{folder_prefix}' mesmo após retries: {e}")
        return None
    except Exception as e:
        print(f" -> ERRO ao processar '{folder_prefix}': {e}")
        return None

def create_vector_database_from_s3():
    print("Iniciando processo de indexação PARALELA por CONJUNTO DE DADOS...")
    
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix='dataset/', Delimiter='/')
    if 'CommonPrefixes' not in response:
        print("Nenhuma subpasta de dataset encontrada.")
        return

    dataset_folders = [p['Prefix'] for p in response.get('CommonPrefixes', [])]
    documents_to_index = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_folder = {executor.submit(process_folder, folder): folder for folder in dataset_folders}
        for future in concurrent.futures.as_completed(future_to_folder):
            result = future.result()
            if result:
                documents_to_index.append(result)

    if not documents_to_index:
        print("\nNenhum documento válido foi gerado para indexar.")
        return

    print(f"\nProcessamento paralelo finalizado. {len(documents_to_index)} conjuntos de dados prontos para indexar.")
    print("Criando e persistindo a base de dados vetorial...")
    
    vector_db = Chroma.from_documents(documents=documents_to_index, embedding=embedding_function, persist_directory=DB_PATH)
    vector_db.persist()
    
    print(f"\nBase de vetores final criada com sucesso em '{DB_PATH}' com {len(documents_to_index)} conjuntos de dados lógicos.")

if __name__ == "__main__":
    create_vector_database_from_s3()