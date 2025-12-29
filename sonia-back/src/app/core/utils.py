# src/s3_utils.py

import os
import re
import time
import boto3
import pandas as pd
from botocore import UNSIGNED
from botocore.config import Config
from typing import List

s3_client = boto3.client('s3', region_name='sa-east-1', config=Config(signature_version=UNSIGNED))
BUCKET_NAME = "ons-aws-prod-opendata"

# --- Sistema de Cache em Memória ---
_file_cache = {}
_CACHE_TTL_SECONDS = 3600  # 1 hora

def find_actual_data_files(dataset_slug: str, use_cache: bool = True) -> List[str]:
    """Encontra os ficheiros de dados no S3 para um dado slug, com cache."""
    cache_key = dataset_slug
    
    # Verifica a cache primeiro
    if use_cache and cache_key in _file_cache:
        cached_data = _file_cache[cache_key]
        if time.time() - cached_data['timestamp'] < _CACHE_TTL_SECONDS:
            print(f"INFO: A usar cache para as partições de '{dataset_slug}'.")
            return cached_data['files']

    print(f"INFO: A procurar no S3 por partições de '{dataset_slug}'.")
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
        
        # Armazena o resultado na cache
        _file_cache[cache_key] = {'files': files, 'timestamp': time.time()}
        return files
        
    except Exception as e:
        print(f"Erro ao listar arquivos S3 para {dataset_slug}: {e}")
        return []

def load_df_from_s3(s3_uri: str) -> pd.DataFrame:
    """Carrega um DataFrame a partir de um URI do S3."""
    storage_options = {'anon': True, 'client_kwargs': {'region_name': 'sa-east-1'}}
    file_name = os.path.basename(s3_uri)
    try:
        if s3_uri.lower().endswith('.csv'):
            df = pd.read_csv(s3_uri, storage_options=storage_options, delimiter=';', on_bad_lines='skip')
            if df.shape[1] == 1:
                df = pd.read_csv(s3_uri, storage_options=storage_options, delimiter=',', on_bad_lines='skip')
        elif s3_uri.lower().endswith('.parquet'):
            df = pd.read_parquet(s3_uri, storage_options=storage_options)
        else:
            raise ValueError(f"Formato de ficheiro não suportado para {file_name}.")
        print(f"INFO: Ficheiro {file_name} carregado com sucesso. Shape: {df.shape}")
        return df
    except Exception as e:
        raise ValueError(f"Não foi possível carregar o ficheiro {s3_uri}. Erro: {e}")