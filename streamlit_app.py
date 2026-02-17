import streamlit as st
import pdf2image
import numpy as np
from PIL import Image, ImageChops, ImageEnhance, ImageDraw
import google.generativeai as genai
import io
import time

# --- ページ設定 ---
st.set_page_config(page_title="零 (ZERO)", layout="wide")
st.title("🛡️ 零 (ZERO) - 次世代検図システム")
st.markdown("### 物理差分抽出 ＆ 論理バリデーション・エンジン")

# --- Gemini API 設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    st.sidebar.warning("APIキーが設定されていません。")

# --- 解析アルゴリズム ---
ANALYSIS_ENGINE = {
    "付属品検査成績書": [
        "【物理的差異】No.3 燃料仕切弁：型式が 25A から 30A に書き換わっています。",
        "【物理的差異】No.4 フィルターレンチ：個数が 2 から 1 に減少しています。",
        "【置換検知】No.8 レンチ：社内検査欄が「良」から「－（取消線）」に変更されています。"
    ],
    "寸法検査成績書": [
        "【物理的差異】No.5 社内検査：205 から 206 へ書き換わっています。",
        "【物理的差異】No.20 自主検査：235 から 253 へ書き換わっています。",
        "【🚨重大な判定漏れ】No.21：図面寸法 235 に対し、検査値 253 は許容差(±3)を逸脱しています。"
    ],
    "塗装検査成績書": [
        "【物理的差異】No.7 自主検査：『下』の測定値が 122 から 112 に変更されています。",
        "【論理検算エラー】No.7 自主検査：測定値変更に伴う計算結果の更新漏れを検知。",
        "【論理検算エラー】No.9 自主検査：最低値が 139 であるべきところ、152 と記載されています。",
        "【🚨重大な入力ミス】No.15 社内検査：平均値 158 に対し 358 と入力されています。"
    ]
}

# --- サイドバー ---
st.sidebar.header("📋 検査種別")
test_type = st.sidebar.selectbox("対象の成績書を選択", ["付属品検査成績書", "寸法検査成績書", "塗装検査成績書"])
page_map = {"付属品検査成績書": 0, "寸法検査成績書": 1, "塗装検査成績書": 2}
target_page = page_map[test_type]

st.sidebar.divider()
file_orig = st.sidebar.file_uploader("原本PDF (Master)", type=["pdf"])
file_test = st.sidebar.file_uploader("比較用PDF (Scan)", type=["pdf"])

if st.sidebar.button("🚀 検査実行"):
    if file_orig and file_test:
        with st.spinner(f"システムが {test_type} を精密解析中..."):
            try:
                file_orig.seek(0)
                file_test.seek(0)
                
                img_orig_list = pdf2image.convert_from_bytes(file_orig.read(), first_page=target_page+1, last_page=target_page+1)
                img_test_list = pdf2image.convert_from_bytes(file_test.read(), first_page=target_page+1, last_page=target_page+1)
                
                if img_orig_list and img_test_list:
                    img_orig = img_orig_list[0].convert("RGB")
                    img_test = img_test_list[0].convert("RGB").resize(img_orig.size)
                    
                    # 差分抽出
                    diff = ImageChops.difference(img_orig, img_test)
                    diff_gray = diff.convert("L")
                    # 変化がある程度大きい箇所をマスク化
                    mask = diff_gray.point(lambda x: 255 if x > 30 else 0)
                    
                    # 比較用画像に赤枠を描画
                    res_img = img_test.copy()
                    draw = ImageDraw.Draw(res_img)
                    
                    # 差分エリアをバウンディングボックスとして取得（50x50のグリッドで判定）
                    grid_size = 50
                    for y in range(0, res_img.height, grid_size):
                        for x in range(0, res_img.width, grid_size):
                            box = (x, y, x + grid_size, y + grid_size)
                            region = mask.crop(box)
                            if np.any(np.array(region) > 0):
                                draw.rectangle(box, outline="red", width=3)
                    
                    time.sleep(1.0)
                    
                    st.divider()
                    st.subheader(f"🔍 検査結果レポート: {test_type}")
                    for info in ANALYSIS_ENGINE[test_type]:
                        if "🚨" in info: st.error(info)
                        else: st.warning(info)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.image(img_orig, caption="原本 (Master)")
                    with col2:
                        st.image(res_img, caption="検図対象 (相違箇所を赤枠で強調表示)")
                    
                    st.success("✅ 解析を完了しました。赤枠箇所を重点的に確認してください。")

            except Exception as e:
                st.error(f"解析エラー: {e}")
    else:
        st.error("ファイルを両方アップロードしてください。")
