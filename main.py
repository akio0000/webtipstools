import streamlit as st
from register import show_registration
from search import show_search
from minutes import show_minutes_registration
from pathlib import Path
import qrcode
import socket
import os

# ==========================================
# 起動時にコンソールへQRコードを表示する機能
# ==========================================
@st.cache_resource
def print_qr_to_console():
    """
    ネットワークIPを取得し、コンソールにQRコードをアスキーアートで表示する。
    st.cache_resource を使うことで、アプリ起動時の1回だけ実行されるようにします。
    """
    def get_local_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # 外部に接続しに行かなくても、接続を試みるだけで自分のIPがわかる
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    local_ip = get_local_ip()
    port = 8501  # デフォルトポート。変更している場合はここを調整
    url = f"http://{local_ip}:{port}"

    # コンソールへの出力
    print("\n" + "█"*50 )
    print(f" Tipstools Web Server Started!")
    print(f" Network URL: {url}")
    print("█" * 50 + "\n")
    
    try:
        qr = qrcode.QRCode()
        qr.add_data(url)
        # コンソール用にアスキーアートで出力
        # invert=True にすることで、黒背景のコンソールで正しく読み取れるようになります
        qr.print_ascii(invert=True)
        print("\n" + "█"*50 + "\n")
    except Exception as e:
        print(f"QRコードの生成に失敗しました: {e}")

# 起動時に実行
print_qr_to_console()


# ==========================================
# フラグ（ON/OFF　追加していく）
# ==========================================
ENABLE_REGISTRATION = True
ENABLE_MINUTES = False   # 議事録
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
if ENABLE_SEARCH:       menu_options.append("検索")
    
menu = st.sidebar.radio(
    "機能を選択",
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
