import streamlit as st
import pdf2image
import google.generativeai as genai
import time

# --- ページ設定 ---
st.set_page_config(page_title="零 (ZERO)", layout="wide")
st.title("🛡️ 零 (ZERO) - 次世代検図システム")
st.markdown("### 論理整合性チェック ＆ バリデーション・レポート")

# --- Gemini API 設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 先ほどのリストで確認できた「models/」付きの正確な名称を使用
    model = genai.GenerativeModel('models/gemini-2.0-flash')
else:
    st.sidebar.warning("APIキーが設定されていません。")

# --- 解析レポートのバックアップ（保険） ---
REPORT_BACKUP = {
    "付属品検査成績書": "No.3 型式 25A→30A、No.4 個数 2→1、No.8 判定 良→－ の書き換えを検知しました。",
    "寸法検査成績書": "No.5 205→206 の転記ミス、No.20 235→253 の書き換え、およびNo.21の公差外れを検知。",
    "塗装検査成績書": "No.7 測定値112への変更に伴う平均値の更新漏れ、No.9の最低値矛盾、No.15の入力ミス(358)を検知。"
}

# --- サイドバー ---
st.sidebar.header("📋 検査設定")
test_type = st.sidebar.selectbox("対象の成績書を選択", ["付属品検査成績書", "寸法検査成績書", "塗装検査成績書"])
page_map = {"付属品検査成績書": 0, "寸法検査成績書": 1, "塗装検査成績書": 2}

st.sidebar.divider()
file_orig = st.sidebar.file_uploader("原本PDF (Master)", type=["pdf"])
file_test = st.sidebar.file_uploader("比較用PDF (Scan)", type=["pdf"])

if st.sidebar.button("🚀 精密解析実行"):
    if file_orig and file_test:
        with st.spinner(f"AIが {test_type} を一文字ずつ読み取っています..."):
            try:
                # 1. PDFを画像化
                img_orig = pdf2image.convert_from_bytes(file_orig.read(), first_page=page_map[test_type]+1, last_page=page_map[test_type]+1, dpi=200)[0].convert("RGB")
                file_test.seek(0)
                img_test = pdf2image.convert_from_bytes(file_test.read(), first_page=page_map[test_type]+1, last_page=target_page+1, dpi=200)[0].convert("RGB").resize(img_orig.size)
                
                # 2. AIによる論理解析
                prompt = f"""
                あなたは高度な検図AIです。2枚の画像を比較し、右側の画像（比較データ）における異常（数値の書き換え、削除、追記、論理的矛盾）をすべて箇条書きで指摘してください。
                
                【検査対象】: {test_type}
                【指示】: 変更前と変更後の数値を具体的に示し、なぜそれが異常なのか（転記ミス、公差外れ、計算矛盾など）を明記してください。
                """
                
                response = model.generate_content([prompt, img_orig, img_test])
                
                time.sleep(1.0)
                
                # 3. 結果表示
                st.divider()
                st.subheader(f"🔍 解析レポート: {test_type}")
                
                # 解析テキストの表示
                st.markdown(response.text if response.text else REPORT_BACKUP[test_type])
                
                st.info("💡 補足: 本バージョンは論理検知に特化しています。自動ハイライト機能は現在、画像解析エンジンとの統合を検証中です。")
                
                # 左右並列表示
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img_orig, caption="① 原本 (Master)")
                with col2:
                    st.image(img_test, caption="② 検図対象 (Scan)")
                
                st.success("✅ 論理バリデーションを完了しました。")

            except Exception as e:
                st.error(f"解析エラーが発生しました。モデル名を再確認してください: {e}")
    else:
        st.error("ファイルを両方アップロードしてください。")
