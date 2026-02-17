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
st.markdown("### AI自律解析 ＆ 座標特定エンジン（本実装検証版）")

# --- Gemini API 設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 最新の2.5 Proモデルを指定（座標認識能力に優れています）
    model = genai.GenerativeModel('gemini-2.5-pro')
else:
    st.sidebar.warning("APIキーが設定されていません。")

# --- サイドバー ---
st.sidebar.header("📋 検査種別")
test_type = st.sidebar.selectbox("対象の成績書を選択", ["付属品検査成績書", "寸法検査成績書", "塗装検査成績書"])
page_map = {"付属品検査成績書": 0, "寸法検査成績書": 1, "塗装検査成績書": 2}
target_page = page_map[test_type]

file_orig = st.sidebar.file_uploader("原本PDF (Master)", type=["pdf"])
file_test = st.sidebar.file_uploader("比較用PDF (Scan)", type=["pdf"])

if st.sidebar.button("🚀 AI精密解析実行"):
    if file_orig and file_test:
        with st.spinner("AIが画像内の異常をスキャンして座標を特定中... (20〜40秒ほどかかります)"):
            try:
                # 1. PDFを画像化（AIが細部を認識できるようDPI 200に設定）
                img_orig_list = pdf2image.convert_from_bytes(file_orig.read(), first_page=target_page+1, last_page=target_page+1, dpi=200)
                file_test.seek(0)
                img_test_list = pdf2image.convert_from_bytes(file_test.read(), first_page=target_page+1, last_page=target_page+1, dpi=200)
                
                img_orig = img_orig_list[0].convert("RGB")
                img_test = img_test_list[0].convert("RGB").resize(img_orig.size)
                
                # 2. AIへの高度なプロンプト（物体検出モード）
                prompt = f"""
                あなたは製造業の品質保証担当です。
                添付された2枚の画像を比較し、右側の画像（比較データ）における異常（数値の書き換え、削除、追記、論理的矛盾）をすべて特定してください。
                
                回答は以下の形式を厳守してください：
                [ymin, xmin, ymax, xmax] 異常の説明
                
                ※座標は0から1000の正規化座標で答えてください。
                ※重要：対象は「{test_type}」です。
                """
                
                # 画像をAIに送信
                response = model.generate_content([prompt, img_orig, img_test])
                
                # 3. 解析結果の描画
                res_img = img_test.copy()
                draw = ImageDraw.Draw(res_img)
                w, h = res_img.size
                
                # 座標テキストを抽出
                boxes = re.findall(r"\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]", response.text)
                
                st.divider()
                st.subheader(f"🔍 AI解析レポート: {test_type}")
                
                # AIの回答を表示（これが「根拠」になります）
                st.info(response.text)
                
                if not boxes:
                    st.warning("AIは明確な異常箇所の座標を特定できませんでした。解析テキストを確認してください。")
                else:
                    for b in boxes:
                        ymin, xmin, ymax, xmax = map(int, b)
                        # 正規化座標をピクセル座標へ変換
                        left = xmin * w / 1000
                        top = ymin * h / 1000
                        right = xmax * w / 1000
                        bottom = ymax * h / 1000
                        draw.rectangle([left, top, right, bottom], outline="red", width=8)

                # 表示レイアウト
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img_orig, caption="原本 (Master)")
                with col2:
                    st.image(res_img, caption="AI自律判定結果 (座標特定)")
                
                st.success("✅ AIによる本来の検図プロセスが完了しました。")

            except Exception as e:
                st.error(f"解析エラー: {e}")
    else:
        st.error("ファイルを両方アップロードしてください。")
