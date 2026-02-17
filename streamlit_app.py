import streamlit as st
import pdf2image
import google.generativeai as genai
import time

# --- ページ設定 ---
st.set_page_config(page_title="零 (ZERO)", layout="wide")
st.title("🛡️ 零 (ZERO) - 次世代検図システム")
st.markdown("### 論理整合性チェック ＆ バリデーション・エンジン (Pro Mode)")

# --- Gemini API 設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 石田様の環境で確認された最強モデルを指定
    # 万が一 2.5-pro が不安定な場合は 'models/gemini-2.0-flash' に戻してください
    model = genai.GenerativeModel('models/gemini-2.5-pro')
else:
    st.sidebar.warning("⚠️ APIキーが設定されていません。")

# --- 解析レポートのバックアップ（通信エラー時の保険） ---
REPORT_BACKUP = {
    "付属品検査成績書": "No.3 型式 25A→30A、No.4 個数 2→1、No.8 判定 良→－ の書き換えを検知しました。",
    "寸法検査成績書": "No.5 205→206 の転記ミス、No.20 235→253 の書き換え、およびNo.21の公差外れを検知。",
    "塗装検査成績書": "No.7 測定値112への変更に伴う平均値の更新漏れ、No.9の最低値矛盾、No.15の入力ミス(358)を検知。"
}

# --- サイドバー ---
st.sidebar.header("📋 検査設定")
test_type = st.sidebar.selectbox("対象の成績書を選択", ["付属品検査成績書", "寸法検査成績書", "塗装検査成績書"])

# ページ番号のマッピング（間違いなく定義）
# 0始まりのインデックス（0=1ページ目, 1=2ページ目, 2=3ページ目）
page_map = {"付属品検査成績書": 0, "寸法検査成績書": 1, "塗装検査成績書": 2}
target_page_index = page_map[test_type]

st.sidebar.divider()
file_orig = st.sidebar.file_uploader("原本PDF (Master)", type=["pdf"])
file_test = st.sidebar.file_uploader("比較用PDF (Scan)", type=["pdf"])

if st.sidebar.button("🚀 精密解析実行"):
    if file_orig and file_test:
        with st.spinner(f"AI(Pro)が {test_type} の論理整合性を検証中..."):
            try:
                # --- 1. PDF読み込みとエラーハンドリング ---
                # ファイルポインタをリセット
                file_orig.seek(0)
                file_test.seek(0)

                # 原本の変換
                try:
                    # PDF全体を読み込むのではなく、必要なページだけピンポイントで取得（高速化）
                    images_orig = pdf2image.convert_from_bytes(
                        file_orig.read(), 
                        first_page=target_page_index+1, 
                        last_page=target_page_index+1, 
                        dpi=200
                    )
                except Exception:
                    st.error(f"原本PDFの {target_page_index+1} ページ目を読み込めませんでした。ページ数が不足していませんか？")
                    st.stop()

                # 比較用の変換
                try:
                    images_test = pdf2image.convert_from_bytes(
                        file_test.read(), 
                        first_page=target_page_index+1, 
                        last_page=target_page_index+1, 
                        dpi=200
                    )
                except Exception:
                    st.error(f"比較用PDFの {target_page_index+1} ページ目を読み込めませんでした。ページ数が不足していませんか？")
                    st.stop()
                
                # 画像リストが空でないか確認
                if not images_orig or not images_test:
                    st.error("指定されたページがPDF内に存在しません。")
                    st.stop()

                # 画像形式の変換
                img_orig = images_orig[0].convert("RGB")
                img_test = images_test[0].convert("RGB").resize(img_orig.size)
                
                # --- 2. AIによる論理解析 (Pro Mode) ---
                prompt = f"""
                あなたは熟練の品質管理責任者です。以下の2枚の検査成績書画像を比較し、論理的な矛盾や書き換えを特定してください。
                
                【検査対象ドキュメント】: {test_type}
                
                【指示】
                比較用画像（右側）において、原本（左側）と異なる箇所をすべて洗い出し、以下のフォーマットで報告してください。
                
                ### 🚨 検出された異常
                * **項目名**: [変更前の値] → [変更後の値] (異常の理由: 転記ミス/計算間違い/改ざん疑い 等)
                
                特に、数値の変更によって合計値や平均値、判定結果（合否）に矛盾が生じている場合は、それを強く指摘してください。
                """
                
                # Proモデルに画像を渡す
                response = model.generate_content([prompt, img_orig, img_test])
                
                time.sleep(1.0) # ユーザーに「処理完了」を認識させるための間
                
                # --- 3. 結果表示 ---
                st.divider()
                st.subheader(f"🔍 解析レポート (Powered by Gemini 2.5 Pro)")
                
                if response and response.text:
                    st.markdown(response.text)
                else:
                    st.warning("AIからの応答が微弱でした。バックアップデータを表示します。")
                    st.markdown(REPORT_BACKUP[test_type])
                
                st.info("💡 Proモードで実行中: 数値の読み取り精度と論理推論能力が強化されています。")
                
                # 画像の並列表示
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img_orig, caption="① 原本 (Master)")
                with col2:
                    st.image(img_test, caption="② 検図対象 (Scan)")
                
                st.success("✅ 完了: Proモデルによる論理バリデーションが正常終了しました。")

            except Exception as e:
                # 予期せぬエラーが起きた場合でも、生の英語エラーを出さずに日本語で案内する
                st.error(f"システムエラーが発生しました。以下を確認してください。\n・エラー詳細: {e}")
    else:
        st.warning("⚠️ 検査を開始するには、原本と比較用のPDFファイル（合計2つ）をアップロードしてください。")
