import streamlit as st
from pypdf import PdfReader, PdfWriter
import io

# --- ページ設定 ---
st.set_page_config(page_title="PDF 回転アプリ", page_icon="🔄")

# --- アプリのタイトルと説明 ---
st.title("PDF 回転アプリ 🔄")
st.write("PDFファイルをアップロードし、回転方向を選ぶとダウンロードできます。")

# --- 1. ファイルアップローダー ---
uploaded_file = st.file_uploader("ここにPDFファイルをドラッグ＆ドロップ", type="pdf")


# ファイルがアップロードされたら処理を実行
if uploaded_file is not None:
    st.markdown("---")
    
    # --- 2. 回転方向の選択 ---
    option_map = {
        '時計回りに90度 ↪️': 90,
        '反時計回りに90度 ↩️': -90,
        '180度回転 🔄': 180
    }
    
    selected_option = st.radio(
        "回転方向を選択してください:",
        options=option_map.keys(),
        horizontal=True, # 横並びで表示
    )

    st.write("") # スペースを空ける

    # --- 3. PDF回転処理 ---
    try:
        # メモリ上でPDFファイルを読み込む
        input_pdf = PdfReader(uploaded_file)
        output_pdf_writer = PdfWriter()
        
        # 選択された角度を取得
        rotation_angle = option_map[selected_option]

        # 全てのページをループして回転
        for page in input_pdf.pages:
            page.rotate(rotation_angle)
            output_pdf_writer.add_page(page)

        # メモリ上のバイトデータとしてPDFを保存するためのオブジェクト
        pdf_bytes = io.BytesIO()
        output_pdf_writer.write(pdf_bytes)
        # ストリームの先頭にカーソルを戻すことが重要
        pdf_bytes.seek(0)

        # --- 4. ダウンロードボタンの表示 ---
        output_filename = f"rotated_{uploaded_file.name}"
        st.download_button(
            label="📥 回転したPDFをダウンロード",
            data=pdf_bytes,
            file_name=output_filename,
            mime="application/pdf",
            use_container_width=True # ボタンをコンテナの幅に合わせる
        )

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        st.error("暗号化されているか、破損したPDFファイルの可能性があります。")

else:
    st.info("👆 上のボックスからPDFファイルをアップロードして開始してください。")