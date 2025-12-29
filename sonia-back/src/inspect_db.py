# inspect_db.py
from langchain_community.vectorstores import Chroma

DB_PATH = "vector_store_db"

def inspect_database():
    print("--- Inspecionando a Base de Dados Vetorial ---")
    
    # Carrega a base de dados do disco (não precisa de embedding model para isso)
    vector_db = Chroma(persist_directory=DB_PATH)
    
    # Pega todos os documentos e metadados
    # O include garante que pegaremos o conteúdo e os metadados
    results = vector_db.get(include=["metadatas", "documents"])
    
    if not results or not results['ids']:
        print("A base de dados está vazia ou não pôde ser carregada.")
        return

    total_docs = len(results['ids'])
    print(f"Total de {total_docs} documentos encontrados.\n")

    # Imprime cada documento de forma legível
    for i in range(total_docs):
        metadata = results['metadatas'][i]
        document = results['documents'][i]
        source_file = metadata.get('original_filename', 'N/A').replace('.txt', '.csv')

        print(f"Dataset: {source_file}")
        print(f"  Resumo Gerado: '{document}'")
        print("-" * 20)

if __name__ == "__main__":
    inspect_database()