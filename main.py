import streamlit as st
from register import show_registration
from search import show_search
from pathlib import Path

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(
    page_title="Tipsアプリ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# サーバー/保存先パス設定（サイドバー）
# ==========================================
st.sidebar.title("環境設定")
st.sidebar.markdown("※共有データの保存先フォルダ等のパスを直接入力してください")

if "data_dir" not in st.session_state:
    # ここでデフォルトの保存先を設定（変更可能）
    st.session_state["data_dir"] = r"C:\Users\user\Desktop\data"

data_dir_input = st.sidebar.text_input("データ保存先パス", st.session_state["data_dir"])
# 入力されたパスをセッションステートに常に反映
st.session_state["data_dir"] = data_dir_input

# ==========================================
# メインメニュー
# ==========================================
st.sidebar.title("メニュー")

menu = st.sidebar.radio(
    "機能を選択",
    ["登録", "検索"]
)

# ==========================================
# 画面の切り替え
# ==========================================
if menu == "登録":
    show_registration()
elif menu == "検索":
    show_search()
