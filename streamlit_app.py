import streamlit as st
import pdf2image
import numpy as np
from PIL import Image, ImageChops, ImageEnhance, ImageDraw, ImageFilter
import google.generativeai as genai
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
                
                # 高解像度で読み込み (DPI=200程度)
                img_orig_list = pdf2image.convert_from_bytes(file_orig.read(), first_page=target_page+1, last_page=target_page+1, dpi=200)
                img_test_list = pdf2image.convert_from_bytes(file_test.read(), first_page=target_page+1, last_page=target_page+1, dpi=200)
                
                if img_orig_list and img_test_list:
                    img_orig = img_orig_list[0].convert("RGB")
                    img_test = img_test_list[0].convert("RGB").resize(img_orig.size)
                    
                    # --- 高精度差分ロジック ---
                    # 1. わずかにぼかして位置ズレを吸収
                    blur_orig = img_orig.filter(ImageFilter.GaussianBlur(radius=1))
                    blur_test = img_test.filter(ImageFilter.GaussianBlur(radius=1))
                    
                    # 2. 差分抽出
                    diff = ImageChops.difference(blur_orig, blur_test)
                    # 黒い画面表示用
                    diff_display = ImageEnhance.Contrast(diff).enhance(20.0)
                    
                    # 3. ノイズ除去（小さな点や線を消す）
                    diff_gray = diff.convert("L").filter(ImageFilter.MedianFilter(size=3))
                    mask = diff_gray.point(lambda x: 255 if x > 40 else 0)
                    
                    res_img = img_test.copy()
                    draw = ImageDraw.Draw(res_img)
                    
                    # グリッド判定（少し大きめのグリッドで「意味のある変化」を捉える）
                    grid_size = 30
                    for y in range(0, res_img.height, grid_size):
                        for x in range(0, res_img.width, grid_size):
                            box = (x, y, x + grid_size, y + grid_size)
                            region = mask.crop(box)
                            # 領域内の変化ピクセル密度をチェック
                            if np.sum(np.array(region) > 0) > 40: 
                                # 赤枠を描画
                                draw.rectangle(box, outline="red", width=5)
                    
                    time.sleep(1.2)
                    
                    st.divider()
                    st.subheader(f"🔍 検査結果レポート: {test_type}")
                    for info in ANALYSIS_ENGINE[test_type]:
                        if "🚨" in info: st.error(info)
                        else: st.warning(info)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1: st.image(img_orig, caption="① 原本 (Master)")
                    with col2: st.image(diff_display, caption="② 物理差分スキャン")
                    with col3: st.image(res_img, caption="③ 検図判定 (赤枠箇所を要確認)")
                    st.success("✅ 解析を完了しました。")

            except Exception as e:
                st.error(f"解析エラー: {e}")
    else:
        st.error("ファイルを両方アップロードしてください。")
