import streamlit as st
import google.generativeai as genai

st.title("🛡️ 零 (ZERO) - モデル接続テスト")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    try:
        st.write("### 🟢 利用可能なモデル一覧")
        models = genai.list_models()
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                st.code(m.name) # ここに表示される名前が「正解」です
        st.success("APIキーは正常に認証されています。")
    except Exception as e:
        st.error(f"接続エラー: {e}")
else:
    st.error("APIキーがSecretsに設定されていません。")
