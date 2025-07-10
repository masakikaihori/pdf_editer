import streamlit as st
from pypdf import PdfWriter, PdfReader
import io
import re

# --- ページ番号指定文字列を解析する関数 ---
def parse_page_numbers(page_str, max_pages):
    """
    "1, 3-5, 8"のような文字列をページのインデックスリスト[0, 2, 3, 4, 7]に変換する。
    無効なページ番号は無視する。
    """
    pages = set()
    # 無効な文字を削除し、カンマで分割
    parts = re.split(r'[,\s]+', page_str.strip())
    for part in parts:
        if not part:
            continue
        try:
            # "3-5" のような範囲指定を処理
            if '-' in part:
                start, end = map(int, part.split('-'))
                if start > end:
                    start, end = end, start # 順序が逆でも対応
                for i in range(start, end + 1):
                    if 1 <= i <= max_pages:
                        pages.add(i - 1) # 0-indexedに変換
            # 単一のページ番号を処理
            else:
                page_num = int(part)
                if 1 <= page_num <= max_pages:
                    pages.add(page_num - 1) # 0-indexedに変換
        except ValueError:
            # 数字に変換できないものは無視
            continue
    return sorted(list(pages))


# --- Streamlit アプリケーションのUI ---
st.set_page_config(page_title="PDFページ抽出・結合", layout="wide")

st.title("📄 PDF特定ページの抽出・結合アプリ")
st.markdown("""
このアプリは、複数のPDFファイルから特定のページだけを抽出し、好きな順番で一つのPDFに結合します。
""")

# --- セッションステートの初期化 ---
if 'pdf_data' not in st.session_state:
    st.session_state.pdf_data = []

# --- 1. ファイルのアップロード ---
st.header("1. PDFファイルをアップロード")
uploaded_files = st.file_uploader(
    "結合したいPDFファイルをすべて選択してください。",
    type="pdf",
    accept_multiple_files=True
)

if uploaded_files:
    # --- 2. ページと順序の指定 ---
    st.header("2. 抽出するページと結合順序を指定")
    st.info("💡 結合したい順番に入力してください。")

    # ファイルごとにページ指定UIを作成
    if 'ordered_files' not in st.session_state:
        st.session_state.ordered_files = uploaded_files
    
    # ユーザーが並べ替えるためのコンテナ
    file_order_container = st.container()
    with file_order_container:
        # このキーをセッションステートに保存することで、並べ替えの状態を維持
        if 'file_order_keys' not in st.session_state:
            st.session_state.file_order_keys = [f.name for f in uploaded_files]

        # ユーザーが並べ替えたファイルリストを作成
        # st.multiselectを使用してドラッグ＆ドロップUIを実現
        ordered_file_names = st.multiselect(
            "結合順序:",
            options=[f.name for f in uploaded_files],
            default=[f.name for f in uploaded_files],
            label_visibility="collapsed"
        )
        
        # ファイル名から元のアップロードオブジェクトを引けるように辞書を作成
        uploaded_file_dict = {f.name: f for f in uploaded_files}

    # 各ファイルの設定
    page_selections = {}
    for filename in ordered_file_names:
        file = uploaded_file_dict[filename]
        
        # 各ファイルのエキスパンダーを作成
        with st.expander(f"ファイル: **{file.name}**"):
            try:
                # PDFをメモリ上で読み込み、総ページ数を取得
                reader = PdfReader(io.BytesIO(file.getvalue()))
                max_pages = len(reader.pages)
                st.markdown(f"（総ページ数: {max_pages}）")
                
                # ページ番号入力欄
                page_str = st.text_input(
                    "抽出するページ番号を入力 (例: `1, 3-5, 8`)",
                    placeholder="すべてのページを抽出する場合は空欄のまま",
                    key=f"pages_{file.name}"
                )
                page_selections[file.name] = (page_str, max_pages)

            except Exception as e:
                st.error(f"ファイル「{file.name}」の読み込み中にエラーが発生しました: {e}")


    # --- 3. 結合の実行 ---
    st.header("3. 結合を実行")
    if st.button("🚀 PDFを結合する", type="primary"):
        writer = PdfWriter()
        
        with st.spinner("PDFを結合しています..."):
            try:
                # 指定された順序でファイルを処理
                for filename in ordered_file_names:
                    file = uploaded_file_dict[filename]
                    page_str, max_pages = page_selections[filename]
                    
                    # PDFリーダーを再度作成
                    reader = PdfReader(io.BytesIO(file.getvalue()))
                    
                    # ページ指定がない場合は全ページを追加
                    if not page_str.strip():
                        pages_to_add = range(max_pages)
                    else:
                        pages_to_add = parse_page_numbers(page_str, max_pages)

                    if not pages_to_add and page_str.strip():
                         st.warning(f"ファイル「{filename}」で有効なページが指定されなかったため、スキップします。")
                         continue

                    # 指定されたページをwriterに追加
                    for page_index in pages_to_add:
                        writer.add_page(reader.pages[page_index])
                
                # 結合したPDFをメモリ上のバイナリデータとして保存
                output_pdf_bytes = io.BytesIO()
                writer.write(output_pdf_bytes)
                # ポインタを先頭に戻す
                output_pdf_bytes.seek(0)
                
                st.session_state.pdf_data = output_pdf_bytes.getvalue()
                st.success("✅ PDFの結合が完了しました！下のボタンからダウンロードしてください。")

            except Exception as e:
                st.error(f"結合処理中にエラーが発生しました: {e}")
                st.session_state.pdf_data = [] # エラー時はデータをクリア

# --- 4. ダウンロード ---
if st.session_state.pdf_data:
    st.header("4. 結合したPDFをダウンロード")
    st.download_button(
        label="📥 結合済みPDFをダウンロード",
        data=st.session_state.pdf_data,
        file_name="merged_pages.pdf",
        mime="application/pdf"
    )