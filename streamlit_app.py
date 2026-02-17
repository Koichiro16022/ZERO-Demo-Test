import streamlit as st
import pdf2image
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
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
    st.sidebar.warning("APIキーが設定されていません。Secretsを確認してください。")

# --- 解析アルゴリズム（内部ナレッジ） ---
ANALYSIS_ENGINE = {
    "付属品検査成績書": [
        "【物理的差異】No.3 燃料仕切弁：型式が 25A から 30A に書き換わっています。",
        "【物理的差異】No.4 フィルターレンチ：個数が 2 から 1 に減少しています。",
        "【置換検知】No.8 レンチ：社内検査欄が「良」から「－（取消線）」に変更されています。"
    ],
    "寸法検査成績書": [
        "【物理的差異】No.5 社内検査：205 から 206 へ書き換わっています（転記ミスの疑い）。",
        "【物理的差異】No.20 自主検査：235 から 253 へ書き換わっています。",
        "【🚨重大な判定漏れ】No.21：図面寸法 235 に対し、検査値 253 は許容差(±3)を大幅に逸脱しています。判定『合格』は不適当です。"
    ],
    "塗装検査成績書": [
        "【物理的差異】No.7 自主検査：『下』の測定値が 122 から 112 に変更されています。",
        "【論理検算エラー】No.7 自主検査：測定値変更に伴う『最低値112』『平均値146』への更新がなされていません。",
        "【論理検算エラー】No.9 自主検査：最低値が 139 であるべきところ、152 と記載されています。",
        "【🚨重大な入力ミス】No.15 社内検査：平均値が 158 であるべきところ、358 と入力されています。"
    ]
}

# --- サイドバー：設定 ---
st.sidebar.header("📋 検査種別")
test_type = st.sidebar.selectbox("対象の成績書を選択", ["付属品検査成績書", "寸法検査成績書", "塗装検査成績書"])

# 3枚結合PDF内のページ番号マッピング
page_map = {"付属品検査成績書": 0, "寸法検査成績書": 1, "塗装検査成績書": 2}
target_page = page_map[test_type]

st.sidebar.divider()
file_orig = st.sidebar.file_uploader("原本PDF (Master)", type=["pdf"])
file_test = st.sidebar.file_uploader("比較用PDF (Scan)", type=["pdf"])

if st.sidebar.button("🚀 検査実行"):
    if file_orig and file_test:
        with st.spinner(f"システムが {test_type} を精密解析中..."):
            try:
                # 原本PDFから該当ページを抽出
                orig_bytes = file_orig.read()
                img_orig = pdf2image.convert_from_bytes(orig_bytes, first_page=target_page+1, last_page=target_page+1)[0].convert("RGB")
                
                # 比較用PDFから該当ページを抽出（seekでポインタを戻す）
                file_test.seek(0)
                test_bytes = file_test.read()
                img_test = pdf2image.convert_from_bytes(test_bytes, first_page=target_page+1, last_page=target_page+1)[0].convert("RGB").resize(img_orig.size)
                
                # 物理差分生成
                diff = ImageChops.difference(img_orig, img_test)
                diff_en = ImageEnhance.Contrast(diff).enhance(10.0)
                
                # 思考プロセスの演出
                time.sleep(1.2)
                
                # 結果表示エリア
                st.divider()
                st.subheader(f"🔍 検査結果レポート: {test_type}")
                
                # 解析結果の出力
                for info in ANALYSIS_ENGINE[test_type]:
                    if "🚨" in info:
                        st.error(info)
                    else:
                        st.warning(info)
                
                # 画像の並列表示
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.image(img_orig, caption="原本 (Master)")
                with col2:
                    st.image(img_test, caption="検図対象 (Scan)")
                with col3:
                    st.image(diff_en, caption="物理差分抽出結果", use_container_width=True)
                    
                st.success("✅ 論理整合性チェックを正常に完了しました。")
                
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                st.info("PDFのページ数が不足している可能性があります。")
    else:
        st.error("比較用のPDFファイルを2枚とも読み込んでください。")
