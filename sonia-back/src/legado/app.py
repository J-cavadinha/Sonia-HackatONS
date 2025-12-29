# src/app.py (código completo e atualizado)

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os
import pandas as pd
import re
from collections import defaultdict
from core_logic import find_relevant_datasets, load_df_from_s3
from analysis_agent import run_multi_df_analysis

if "messages" not in st.session_state:
    st.session_state.messages = []
if "dataframes" not in st.session_state:
    st.session_state.dataframes = []

st.set_page_config(layout="wide")
st.title("Assistente de Análise de Dados Conversacional 💬")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "tokens" in message:
            st.caption(f"Custo da operação: {message['tokens']} tokens")

if prompt := st.chat_input("Faça uma pergunta sobre os dados..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        total_tokens_this_turn = 0
        st.session_state.dataframes = []

        with st.spinner("A identificar e carregar os conjuntos de dados..."):
            # --- ALTERAÇÃO 1: A CHAMADA AGORA RETORNA DADOS PRONTOS PARA USO ---
            all_dossiers, all_uris, selection_tokens = find_relevant_datasets(prompt)
            total_tokens_this_turn += selection_tokens
            
            if not all_uris:
                st.warning("Nenhum conjunto de dados relevante foi encontrado para a sua pergunta.")
                st.stop()
            
            combined_dossier = "\n\n---\n\n".join(all_dossiers)
            
            # --- ALTERAÇÃO 2: LÓGICA DE SELEÇÃO DE FICHEIROS SIMPLIFICADA ---
            uris_to_load = []
            if all_uris:
                grouped_uris = defaultdict(list)
                for uri in all_uris:
                    base_name = re.sub(r'_\d{4}', '', os.path.splitext(os.path.basename(uri))[0])
                    grouped_uris[base_name].append(uri)

                for base_name, uri_list in grouped_uris.items():
                    if not uri_list: continue
                    
                    def extract_year_from_uri(uri):
                        match = re.search(r'(\d{4})', uri)
                        return int(match.group(1)) if match else 0

                    latest_uri = max(uri_list, key=extract_year_from_uri)
                    uris_to_load.append(latest_uri)

            uris_to_load = sorted(list(set(uris_to_load)))
            
            if not uris_to_load:
                st.warning("O conjunto de dados encontrado não continha ficheiros de dados válidos.")
                st.stop()
                
            st.success(f"{len(all_dossiers)} conjunto(s) de dados encontrados. A carregar {len(uris_to_load)} ficheiro(s) mais recente(s) para análise.")

            loaded_dfs = []
            progress_bar = st.progress(0, text="A iniciar o carregamento...")
            for i, uri in enumerate(uris_to_load):
                try:
                    df = load_df_from_s3(uri)
                    df_name = os.path.basename(uri).replace('.csv', '').replace('.parquet', '')
                    df.name = df_name
                    loaded_dfs.append(df)
                    progress_bar.progress((i + 1) / len(uris_to_load), text=f"A carregar {df_name}...")
                except Exception as e:
                    st.error(f"Não foi possível carregar o ficheiro {uri}. Erro: {e}")
            progress_bar.empty()
            
            if not loaded_dfs:
                st.error("Nenhum ficheiro de dados pôde ser carregado.")
                st.stop()
                
            st.session_state.dataframes = loaded_dfs

        with st.spinner("O agente está a pensar..."):
            try:
                history = st.session_state.messages[:-1]
                response = run_multi_df_analysis(st.session_state.dataframes, prompt, history, combined_dossier)
                
                analysis_tokens = response.get('total_tokens', 0)
                total_tokens_this_turn += analysis_tokens
                final_answer = response.get('output', 'Não foi possível obter uma resposta.')
                
                if "Agent stopped" in final_answer:
                    final_answer = "A sua pergunta é muito complexa. Por favor, tente reformular de forma mais simples."

                st.markdown(final_answer)
                st.caption(f"Custo total da resposta: {total_tokens_this_turn} tokens")

                assistant_message = {"role": "assistant", "content": final_answer, "tokens": total_tokens_this_turn}
                st.session_state.messages.append(assistant_message)

            except Exception as e:
                st.error(f"Ocorreu um erro durante a análise: {e}")