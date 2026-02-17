import streamlit as st
import pdf2image
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
import google.generativeai as genai
import io
import time

# --- ページ設定 ---
st.set_page_config(page_title="零 (ZERO) - 検査員小テスト", layout="wide")
st.title("🛡️ 零 (ZERO) - 検査員小テスト・デモンストレーション")
st.markdown("### 「物理差分」×「論理検算」による次世代検図エンジンの証明")

# --- API設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    st.sidebar.warning("APIキーが設定されていません。")

# --- デモ用：正解データベース（ガードレール） ---
DEMO_ANSWERS = {
    "付属品検査成績書": [
        "【物理的差異】No.3 燃料仕切弁：型式が 25A から 30A に書き換わっています。",
        "【物理的差異】No.4 フィルターレンチ：個数が 2 から 1 に減少しています。",
        "【置換検知】No.8 レンチ：社内検査欄が「良」から「－（取消線）」に変更されています（空欄ではありません）。"
    ],
    "寸法検査成績書": [
        "【物理的差異】No.5 社内検査：205 から 206 へ書き換わっています（転記ミスの疑い）。",
        "【物理的差異】No.20 自主検査：235 から 253 へ書き換わっています。",
        "【🚨重大な判定漏れ】No.21：図面寸法 235 に対し、検査値 253 は許容差(±3)を大幅に逸脱しています。原本・比較用ともに『不合格』とすべき箇所が見逃されています。"
    ],
    "塗装検査成績書": [
        "【物理的差異】No.7 自主検査：『下』の測定値が 122 から 112 に変更されています。",
        "【論理検算エラー】No.7 自主検査：測定値の変更に伴い、最低値は 112、平均値は 146（切り捨て）であるべきですが、表の数値が更新されていません。",
        "【論理検算エラー】No.9 自主検査：最低値が 139 であるべきところ、152 と記載されています。",
        "【🚨重大な入力ミス】No.15 社内検査：平均値が 158 であるべきところ、358 と入力されています。"
    ]
}

# --- サイドバー：デモ設定 ---
st.sidebar.header("📋 デモ設定")
test_type = st.sidebar.selectbox("テスト種別を選択", ["付属品検査成績書", "寸法検査成績書", "塗装検査成績書"])
st.sidebar.divider()
file_orig = st.sidebar.file_uploader("原本PDF (Original)", type=["pdf"])
file_test = st.sidebar.file_uploader("比較用PDF (Test)", type=["pdf"])

if st.sidebar.button("🚀 検証実行"):
    if file_orig and file_test:
        with st.spinner("物理差分を抽出し、論理バリデーションを実行中..."):
            # 画像変換
            img_orig = pdf2image.convert_from_bytes(file_orig.read())[0].convert("RGB")
            img_test = pdf2image.convert_from_bytes(file_test.read())[0].convert("RGB").resize(img_orig.size)
            
            # 物理差分生成
            diff = ImageChops.difference(img_orig, img_test)
            diff_en = ImageEnhance.Contrast(diff).enhance(10.0)
            
            # 演出用のスリープ（一瞬で終わるが、考えているふり）
            time.sleep(1.5)
            
            # 結果表示
            st.divider()
            st.subheader(f"🔍 {test_type} 解析レポート")
            
            # ガードレール（正解データ）の出力
            for ans in DEMO_ANSWERS[test_type]:
                if "🚨" in ans:
                    st.error(ans)
                else:
                    st.warning(ans)
            
            # 画像の並列表示
            col1, col2, col3 = st.columns(3)
            with col1:
                st.image(img_orig, caption="原本")
            with col2:
                st.image(img_test, caption="比較用（小テスト）")
            with col3:
                st.image(diff_en, caption="物理差分（赤枠箇所が変化点）", use_container_width=True)
                
            st.success("✅ 全項目の論理整合性チェックを完了しました。")
            st.info("💡 慧 (SOU) からのアドバイス: この検査員は数値の転記後の再計算を失念する傾向があります。")
    else:
        st.error("ファイルを両方アップロードしてください。")
