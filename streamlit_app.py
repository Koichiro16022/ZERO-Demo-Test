import streamlit as st
import pdf2image
import numpy as np
from PIL import Image, ImageDraw
import google.generativeai as genai
import time

# --- ページ設定 ---
st.set_page_config(page_title="零 (ZERO) - AI検証版", layout="wide")
st.title("🛡️ 零 (ZERO) - 次世代検図システム")
st.markdown("### AIによる座標特定 ＆ 論理バリデーション（検証用）")

# Gemini API 設定
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 座標特定に強い最新モデルを使用
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    st.sidebar.warning("APIキーが設定されていません。")

# --- サイドバー ---
st.sidebar.header("📋 検査種別")
test_type = st.sidebar.selectbox("対象の成績書を選択", ["付属品検査成績書", "寸法検査成績書", "塗装検査成績書"])
page_map = {"付属品検査成績書": 0, "寸法検査成績書": 1, "塗装検査成績書": 2}
target_page = page_map[test_type]

file_orig = st.sidebar.file_uploader("原本PDF (Master)", type=["pdf"])
file_test = st.sidebar.file_uploader("比較用PDF (Scan)", type=["pdf"])

if st.sidebar.button("🚀 AI精密検査実行"):
    if file_orig and file_test:
        with st.spinner("AIが画像内の座標を特定中... (15〜30秒ほどかかります)"):
            try:
                # 1. PDFを画像化（DPIを150に抑えて転送速度を確保）
                img_orig_list = pdf2image.convert_from_bytes(file_orig.read(), first_page=target_page+1, last_page=target_page+1, dpi=150)
                file_test.seek(0)
                img_test_list = pdf2image.convert_from_bytes(file_test.read(), first_page=target_page+1, last_page=target_page+1, dpi=150)
                
                img_orig = img_orig_list[0].convert("RGB")
                img_test = img_test_list[0].convert("RGB").resize(img_orig.size)
                
                # 2. AIへのプロンプト（座標特定を依頼）
                prompt = f"""
                あなたは精密な検図システムです。
                2枚の画像を比較し、右側の画像（比較データ）において左側の画像（原本）から「書き換えられた数値」や「異常」がある箇所を特定してください。
                
                回答は必ず以下のJSON形式のみで出力してください。
                [
                  {{"box_2d": [ymin, xmin, ymax, xmax], "label": "異常の内容"}}
                ]
                ※座標は0-1000の数値で指定してください。
                今回の検査対象: {test_type}
                """
                
                # 画像をAIに送信
                response = model.generate_content([prompt, img_orig, img_test])
                
                # 3. AIの回答から赤枠を描画
                res_img = img_test.copy()
                draw = ImageDraw.Draw(res_img)
                w, h = res_img.size
                
                # AIが返した座標テキストを解析して枠を描く（簡易実装）
                import re
                boxes = re.findall(r"\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]", response.text)
                
                for b in boxes:
                    ymin, xmin, ymax, xmax = map(int, b)
                    # 0-1000の座標をピクセルに変換
                    draw.rectangle([xmin * w / 1000, ymin * h / 1000, xmax * w / 1000, ymax * h / 1000], outline="red", width=5)

                st.divider()
                st.subheader(f"🔍 AI解析レポート: {test_type}")
                st.write(response.text) # AIの思考（座標データ）を表示
                
                col1, col2 = st.columns(2)
                with col1: st.image(img_orig, caption="原本")
                with col2: st.image(res_img, caption="AI特定結果（赤枠）")
                
                st.success("✅ AIによる座標特定を完了しました。")

            except Exception as e:
                st.error(f"解析エラー: {e}")
