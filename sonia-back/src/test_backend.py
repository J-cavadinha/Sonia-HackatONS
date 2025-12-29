from dotenv import load_dotenv
load_dotenv()

from core_logic import find_relevant_datasets, load_df_from_s3

print("--- INICIANDO TESTE DO BACKEND ---")

pergunta = "Qual a idade dos clientes?"
uris_encontradas = find_relevant_datasets(pergunta)
print(f"URIs encontrados: {uris_encontradas}")

if uris_encontradas:
    # Exemplo: Carregar o primeiro dataframe da lista
    uri_encontrada = uris_encontradas[0]
    dataframe = load_df_from_s3(uri_encontrada)
    print("DataFrame carregado com sucesso:")
    print(dataframe.head())

print("--- TESTE DO BACKEND FINALIZADO ---")