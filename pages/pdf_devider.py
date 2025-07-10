import streamlit as st
import os
import re
import shutil
import tempfile
from pypdf import PdfReader, PdfWriter

# --- Core PDF Processing Function ---
def process_pdf(input_stream, page_ranges_str, output_dir):
    """
    PDFを指定ページで分割・結合し、出力ディレクトリに保存する関数。
    
    :param input_stream: アップロードされたPDFファイルのデータストリーム。
    :param page_ranges_str: ユーザーが入力したページ範囲の文字列。
    :param output_dir: 分割されたファイルの保存先ディレクトリ。
    :return: 処理中にエラーが発生した場合はエラーメッセージ文字列、成功した場合はNone。
    """
    try:
        reader = PdfReader(input_stream)
        total_pages = len(reader.pages)
        file_basename = "split_pdf" # Use a generic name

        # 全ページを個別に分割する場合
        if not page_ranges_str.strip():
            st.info(f"全 {total_pages} ページを個別に分割します...")
            for i, page in enumerate(reader.pages):
                writer = PdfWriter()
                writer.add_page(page)
                output_filename = os.path.join(output_dir, f"{file_basename}_page_{i + 1}.pdf")
                with open(output_filename, "wb") as f_out:
                    writer.write(f_out)
        # 指定された範囲で分割・結合する場合
        else:
            output_file_definitions = page_ranges_str.split(';')
            progress_bar = st.progress(0, text="分割処理を実行中…")
            
            for i, definition in enumerate(output_file_definitions):
                definition = definition.strip()
                if not definition: continue

                writer = PdfWriter()
                page_ranges = definition.split(',')
                for r in page_ranges:
                    r = r.strip()
                    if '-' in r:
                        start, end = map(int, r.split('-'))
                        for page_num in range(start, end + 1):
                            if 0 < page_num <= total_pages:
                                writer.add_page(reader.pages[page_num - 1])
                    else:
                        page_num = int(r)
                        if 0 < page_num <= total_pages:
                            writer.add_page(reader.pages[page_num - 1])
                
                if len(writer.pages) > 0:
                    safe_definition_name = re.sub(r'[\\/*?:"<>|]', '_', definition)
                    output_filename = os.path.join(output_dir, f"{file_basename}_pages_{safe_definition_name}.pdf")
                    with open(output_filename, "wb") as f_out:
                        writer.write(f_out)
                
                # プログレスバーを更新
                progress_bar.progress((i + 1) / len(output_file_definitions), text=f"ファイル「{definition}」を作成中…")
            
            progress_bar.empty() # 完了したらプログレスバーを消す
        
        return None # 成功
    
    except Exception as e:
        return f"エラーが発生しました: {e}" # 失敗

# --- Streamlit App UI ---

# アプリのタイトルと説明
st.set_page_config(page_title="PDF 分割・結合ツール", page_icon="📄")
st.title("📄 PDF 分割・結合ツール")
st.info("PDFファイルをアップロードし、指定したページ範囲で分割・結合して、zipファイルとしてダウンロードできます。")

# セッション状態の初期化
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'zip_buffer' not in st.session_state:
    st.session_state.zip_buffer = None

# STEP 1: ファイルアップロード
uploaded_file = st.file_uploader("PDFファイルをここにドラッグ＆ドロップするか、選択してください。", type="pdf")

if uploaded_file is not None:
    # STEP 2: ページ範囲とファイル名の指定
    st.markdown("---")
    st.subheader("⚙️ STEP 2: 分割方法とファイル名を設定")
    
    page_ranges_str = st.text_input(
        label="ページ範囲を入力",
        value="1-5; 6-10",
        help="""
        - **複数のファイルに分ける場合**は、範囲をセミコロン（`;`）で区切ります。(例: `1-5; 6-10`)\n
        - **1つのファイルに離れたページをまとめる場合**は、カンマ（`,`）で区切ります。(例: `1, 5-7`)\n
        - **全ページを1ページずつ分割する場合**は、入力欄を**空**にしてください。
        """
    )

    output_zip_name = st.text_input(
        label="出力するzipファイル名（拡張子なし）",
        value="processed_pdf"
    )

    # STEP 3: 実行ボタン
    st.markdown("---")
    if st.button("分割を実行", type="primary"):
        st.session_state.processing = True
        st.session_state.zip_buffer = None

        # 一時ディレクトリを使用して安全にファイルを処理
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = os.path.join(temp_dir, "output_files")
            os.makedirs(output_dir)

            # PDF処理を実行
            error = process_pdf(uploaded_file, page_ranges_str, output_dir)

            if error:
                st.error(error)
                st.session_state.processing = False
            elif not os.listdir(output_dir):
                st.warning("指定されたページが見つからなかったため、ファイルは作成されませんでした。")
                st.session_state.processing = False
            else:
                # 出力ファイルをzipにまとめる
                zip_path_base = os.path.join(temp_dir, output_zip_name)
                shutil.make_archive(zip_path_base, 'zip', output_dir)
                
                zip_path = f"{zip_path_base}.zip"

                # zipファイルの中身をメモリに読み込んでセッションに保存
                with open(zip_path, "rb") as f:
                    st.session_state.zip_buffer = f.read()

# 処理が完了し、ダウンロード準備ができた場合
if st.session_state.processing and st.session_state.zip_buffer:
    st.markdown("---")
    st.success("✅ 処理が完了しました！下のボタンからダウンロードしてください。")
    
    st.download_button(
        label="📥 zipファイルをダウンロード",
        data=st.session_state.zip_buffer,
        file_name=f"{output_zip_name}.zip",
        mime="application/zip",
        on_click=lambda: st.session_state.clear() # ダウンロード後に状態をリセット
    )

st.markdown("---")
st.markdown("<div style='text-align: center; font-size: small;'>Made with Streamlit</div>", unsafe_allow_html=True)