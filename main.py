import streamlit as st
from register import show_registration
from search import show_search
from minutes import show_minutes_registration
from pathlib import Path

# ==========================================
# フラグ（ON/OFF　追加していく）
# ==========================================
ENABLE_REGISTRATION = True
ENABLE_MINUTES = False   # 議事録
ENABLE_BILLING = False   # 会計
ENABLE_SEARCH = True

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
st.sidebar.title("保存先の設定")
st.sidebar.markdown("※データの保存先フォルダのパスを直接入力してください")

if "data_dir" not in st.session_state:
    # デフォルトの保存先（変更可能）
    st.session_state["data_dir"] = r"C:\Users\user\Desktop\data"

data_dir_input = st.sidebar.text_input("データ保存先パス", st.session_state["data_dir"])
# 入力されたパスを常に反映
st.session_state["data_dir"] = data_dir_input

# ==========================================
# メインメニュー
# ==========================================
st.sidebar.title("メニュー")

# ONになっている機能でメニュー作成　追加忘れずに
menu_options = []
if ENABLE_REGISTRATION: menu_options.append("登録")
if ENABLE_MINUTES:      menu_options.append("議事録作成")
if ENABLE_BILLING:      menu_options.append("会計")
if ENABLE_SEARCH:       menu_options.append("検索")
    
menu = st.sidebar.radio(
    "機能を選択",
    ["登録", "検索"]
    menu_options
)

# ==========================================
# 画面の切り替え
# ==========================================
if menu == "登録":
    show_registration()
elif menu == "議事録作成":
    show_minutes_registration()
elif menu == "検索":
    show_search()
