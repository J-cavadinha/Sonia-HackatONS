# src/json_retrieval.py (COM A IMPLEMENTAÇÃO EM DUAS ETAPAS)

from dotenv import load_dotenv
load_dotenv()

import json
import os
import re
from typing import List, Tuple, Dict, Any
from collections import defaultdict
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# --- Modelos Pydantic (sem alterações) ---
class DatasetMatch(BaseModel):
    dataset_slug: str = Field(description="Identificador do conjunto de dados")
    relevance_score: float = Field(description="Pontuação de relevância de 0.0 a 1.0")
    reason: str = Field(description="Explicação breve do por que este conjunto é relevante")

class DatasetSelection(BaseModel):
    relevant_datasets: List[DatasetMatch] = Field(description="Lista de conjuntos de dados relevantes com pontuações")

# --- CLASSE PRINCIPAL MODIFICADA ---
class JSONDatasetRetriever:
    def __init__(self, dictionaries_path: str = "/dictionaries_json"):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.dictionaries_path = os.path.join(base_dir, 'data', 'dictionaries_json')
        print(f"Base Dir detected: {base_dir}")
        print(f"Dictionaries path: {self.dictionaries_path}")
        
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.parser = JsonOutputParser(pydantic_object=DatasetSelection)
        
        # --- NOVO: Carregar e indexar os datasets na inicialização ---
        self.datasets = []
        self.keyword_index = defaultdict(set)
        self.summaries_cache = {}
        self._load_and_index_datasets()

    def _load_and_index_datasets(self):
        """Carrega todos os dicionários JSON e cria um índice de palavras-chave para a filtragem rápida."""
        if not os.path.exists(self.dictionaries_path):
            raise FileNotFoundError(f"O diretório de dicionários não foi encontrado: {self.dictionaries_path}")
        
        for filename in os.listdir(self.dictionaries_path):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(self.dictionaries_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    dataset = json.load(f)
                    self.datasets.append(dataset)
                    
                    # --- Lógica de Indexação (ETAPA 1) ---
                    slug = dataset.get('dataset_slug')
                    if not slug:
                        continue
                    
                    # Indexar palavras do título, descrição e campos
                    text_to_index = [
                        dataset.get('title', ''),
                        dataset.get('description', '')
                    ]
                    for field in dataset.get('fields', []):
                        text_to_index.append(field.get('label', ''))
                        text_to_index.append(field.get('code', ''))
                    
                    # Limpa e tokeniza o texto para criar o índice
                    unique_words = set(re.findall(r'\b\w+\b', ' '.join(filter(None, text_to_index)).lower()))
                    for word in unique_words:
                        self.keyword_index[word].add(slug)

                    # Armazena o resumo em cache para não ter que o recriar
                    self.summaries_cache[slug] = self._create_dataset_summary(dataset)

            except Exception as e:
                print(f"Erro ao carregar ou indexar {filename}: {e}")
        
        print(f"Carregados e indexados {len(self.datasets)} dicionários de conjuntos de dados.")

    def _create_dataset_summary(self, dataset: Dict[str, Any]) -> str:
        """Cria um resumo conciso de um conjunto de dados, incluindo o 'code' das colunas para mais precisão."""
        title = dataset.get('title', '')
        description = dataset.get('description', '')
        slug = dataset.get('dataset_slug', 'N/A')

        fields = dataset.get('fields', [])
        # --- MELHORIA: Incluir 'label' e 'code' para dar mais contexto à IA ---
        key_fields = [f"{field.get('label', 'N/L')} ({field.get('code', 'N/C')})" for field in fields]

        summary = f"Slug: {slug}\nTítulo: {title}\nDescrição: {description}"
        if key_fields:
            summary += "\nCampos principais:\n- " + "\n- ".join(filter(None, key_fields))
        
        return summary

    # --- NOVO MÉTODO (ETAPA 1: FILTRAGEM) ---
    def is_specific_dataset_question(self, question: str):
        """
        Verifica se a pergunta menciona diretamente um dataset pelo slug.
        Retorna (True, slug) se for específica, ou (False, None) caso contrário.
        """
        for dataset in self.datasets:
            slug = dataset.get("dataset_slug")
            if slug and slug.lower() in question.lower():
                return True, slug
        return False, None

    def _filter_candidates(self, user_question: str, top_n: int = 10) -> List[str]:
        """Filtra uma lista de datasets candidatos usando a busca por palavras-chave."""
        question_words = set(re.findall(r'\b\w+\b', user_question.lower()))
        
        candidate_scores = defaultdict(int)
        for word in question_words:
            matching_slugs = self.keyword_index.get(word, set())
            for slug in matching_slugs:
                candidate_scores[slug] += 1
        
        # Ordena os candidatos pela contagem de palavras-chave correspondentes
        sorted_candidates = sorted(candidate_scores.items(), key=lambda item: item[1], reverse=True)
        
        # Retorna os slugs dos N melhores candidatos
        return [slug for slug, score in sorted_candidates[:top_n]]

    # --- MÉTODO PRINCIPAL MODIFICADO (AGORA USA AS DUAS ETAPAS) ---
    def find_relevant_datasets(self, user_question: str, max_datasets: int = 3) -> Tuple[List[str], List[str], int]:
        """
        Encontra datasets relevantes usando um sistema de duas etapas:
        1. Filtra candidatos por palavras-chave.
        2. Usa o LLM para refinar a seleção a partir dos candidatos.
        """
        # ETAPA 1: Filtra os candidatos mais prováveis de forma rápida
        candidate_slugs = self._filter_candidates(user_question)
        
        if not candidate_slugs:
            print("Nenhum candidato encontrado na etapa de filtragem.")
            return [], [], 0

        # Prepara os resumos apenas para os candidatos
        candidate_summaries = []
        for slug in candidate_slugs:
            if slug in self.summaries_cache:
                candidate_summaries.append({
                    'slug': slug,
                    'summary': self.summaries_cache[slug]
                })

        # ETAPA 2: Usa o LLM para a seleção final e refinada
        prompt = f"""
Você é um especialista em análise de dados do Operador Nacional do Sistema Elétrico (ONS). 
Sua tarefa é identificar os conjuntos de dados mais relevantes para responder à pergunta do usuário a partir de uma lista pré-filtrada de candidatos.

**Pergunta do Usuário:** "{user_question}"

**Conjuntos de Dados Candidatos:**
"""
        
        for i, ds in enumerate(candidate_summaries):
            prompt += f"\n{i+1}. Conjunto: {ds['slug']}\n{ds['summary']}\n---"
        
        prompt += f"""

**Instruções:**
1. Analise a pergunta e os campos de cada conjunto de dados candidato para encontrar a melhor correspondência.
2. Retorne apenas os {max_datasets} conjuntos de dados mais relevantes da lista fornecida.
3. Para cada um, forneça uma razão breve e clara para a sua escolha.

**Formato de Resposta (JSON):**
{{
  "relevant_datasets": [
    {{
      "dataset_slug": "nome-do-conjunto-escolhido",
      "relevance_score": 0.9,
      "reason": "Este conjunto é o melhor porque contém as colunas X e Y, que são essenciais para a pergunta."
    }}
  ]
}}

Responda APENAS com o JSON válido, sem texto adicional.
"""
        
        try:
            response = self.llm.invoke(prompt)
            
            # Lógica de parsing robusta
            cleaned_content = response.content.strip().replace('```json', '').replace('```', '').strip()
            parsed_response = json.loads(cleaned_content)
            
            relevant_datasets = parsed_response.get("relevant_datasets", [])
            
            dataset_slugs = [ds.get("dataset_slug", "") for ds in relevant_datasets if ds.get("dataset_slug")]
            dataset_reasons = [ds.get("reason", "") for ds in relevant_datasets if ds.get("dataset_slug")]
            
            # O token count é agora muito menor
            # Uma contagem aproximada baseada em caracteres é mais confiável aqui
            token_count = len(prompt.encode('utf-8')) + len(response.content.encode('utf-8'))
            
            return dataset_slugs, dataset_reasons, token_count
            
        except Exception as e:
            print(f"Erro na correspondência de conjuntos de dados (Etapa 2 - LLM): {e}")
            return [], [], 0

    def get_dataset_info(self, dataset_slug: str) -> Dict[str, Any]:
        """Get full information about a specific dataset."""
        for dataset in self.datasets:
            if dataset.get('dataset_slug') == dataset_slug:
                return dataset
        return {}

# Função de conveniência mantida para compatibilidade, caso seja usada em outros locais.
def find_relevant_datasets_json(user_question: str) -> Tuple[List[str], List[str], int]:
    retriever = JSONDatasetRetriever(dictionaries_path="./dictionaries_json")

    return retriever.find_relevant_datasets(user_question)

if __name__ == "__main__":
    retriever = JSONDatasetRetriever()
    
    test_question = "qual a geração de energia eólica no nordeste?"
    print(f"\n--- Teste com a Pergunta --- \n'{test_question}'")
    
    slugs, reasons, tokens = retriever.find_relevant_datasets(test_question)
    
    print(f"\nSlugs Relevantes Encontrados: {slugs}")
    print(f"Razões para a Escolha: {reasons}")
    print(f"Custo (Tokens Aproximados): {tokens}")