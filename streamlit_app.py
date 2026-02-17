import streamlit as st
import pdf2image
import numpy as np
from PIL import Image, ImageDraw
import google.generativeai as genai
import re
import time

# --- ページ設定 ---
st.set_page_config(page_title="零 (ZERO)", layout="wide")
st.title("🛡️ 零 (ZERO) - 次世代検図システム")
st.markdown("### AIによる座標特定 ＆ 論理バリデーション（本来の実装検証版）")

# --- Gemini API 設定 ---
# エラー回避のため、確実に動作するモデル名に変更しました
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 安定して座標特定が可能なモデルを指定
    model = genai.GenerativeModel('gemini-1.5-pro')
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
        with st.spinner("AIが画像内の異常をスキャンして座標を特定中... (20〜40秒ほどかかります)"):
            try:
                # 1. PDFを画像化（AIが読み取りやすいよう150DPIに設定）
                img_orig_list = pdf2image.convert_from_bytes(file_orig.read(), first_page=target_page+1, last_page=target_page+1, dpi=150)
                file_test.seek(0)
                img_test_list = pdf2image.convert_from_bytes(file_test.read(), first_page=target_page+1, last_page=target_page+1, dpi=150)
                
                img_orig = img_orig_list[0].convert("RGB")
                img_test = img_test_list[0].convert("RGB").resize(img_orig.size)
                
                # 2. AIへの精密プロンプト
                prompt = f"""
                あなたは高度な製造業検図AIです。2枚の画像を比較し、右側の画像（比較データ）において、左側の画像（原本）から数値の書き換え、削除、追記、または論理的な矛盾がある箇所をすべて特定してください。
                
                各異常箇所について、その場所を囲むバウンディングボックスを [ymin, xmin, ymax, xmax] の形式（0から1000の正規化座標）で出力してください。
                
                出力例:
                [350, 400, 450, 600] 数値が100から200に書き換えられている
                [500, 100, 550, 300] 判定が漏れている
                
                検査対象: {test_type}
                """
                
                # 画像をAIに送信（原本と比較データの2枚を渡します）
                response = model.generate_content([prompt, img_orig, img_test])
                
                # 3. AIの回答から赤枠を描画
                res_img = img_test.copy()
                draw = ImageDraw.Draw(res_img)
                w, h = res_img.size
                
                # AIのテキストから [ymin, xmin, ymax, xmax] 形式を抽出
                boxes = re.findall(r"\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]", response.text)
                
                st.divider()
                st.subheader(f"🔍 AI解析レポート: {test_type}")
                
                # 解析テキストを表示
                st.info(response.text)
                
                if not boxes:
                    st.warning("AIが明確な座標を特定できませんでした。解析テキストを確認してください。")
                else:
                    for b in boxes:
                        ymin, xmin, ymax, xmax = map(int, b)
                        # 0-1000の座標をピクセル座標に変換して描画
                        draw.rectangle([xmin * w / 1000, ymin * h / 1000, xmax * w / 1000, ymax * h / 1000], outline="red", width=6)

                # 結果の表示
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img_orig, caption="① 原本 (Master)")
                with col2:
                    st.image(res_img, caption="② AI特定結果 (検出箇所を赤枠で表示)")
                
                st.success("✅ AIによる論理・座標特定プロセスを完了しました。")

            except Exception as e:
                st.error(f"解析エラーが発生しました: {e}")
    else:
        st.error("比較用のファイルをアップロードしてください。")
