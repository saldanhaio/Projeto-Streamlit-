import streamlit as st
import pandas as pd

uploaded_file = st.file_uploader("Suba seu Excel", type="xlsx")

if uploaded_file:
    # Lendo o arquivo e pulando a última linha
    df = pd.read_excel(uploaded_file, skipfooter=1)

    # Exibindo com formatação de moeda
    st.dataframe(
        df,
        column_config={
            "Faturamento Realizado": st.column_config.NumberColumn(
                "Faturamento Realizado",
                help="Valor faturado em Reais",
                format="R$ %.2f",  # Formata com prefixo R$ e 2 casas decimais
            )
        },
        hide_index=True,
    )
