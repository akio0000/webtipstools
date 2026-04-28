import streamlit as st
from register import show_registration
from search import show_search
from minutes import show_minutes_registration
from ai_utils import show_ai_chat
from pathlib import Path
from config import DEFAULT_DATA_DIR
import qrcode
import socket
import os
from utils import migrate_jsons_to_db, get_db_connection

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

# データベース移行の実行
from config import REFERENCE_JSON_DIR
migrate_jsons_to_db(st.session_state.get("data_dir", DEFAULT_DATA_DIR), REFERENCE_JSON_DIR)




# ==========================================
# フラグ（ON/OFF 切り替え）
# ==========================================
ENABLE_REGISTRATION = True
ENABLE_MINUTES = True  # 議事録
ENABLE_SEARCH = True

# 環境変数からAIのデフォルトON/OFFを取得
ENABLE_AI_DEFAULT = os.environ.get("USE_LLM", "1") == "1"

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
st.sidebar.title("環境設定(社内用)")
st.sidebar.markdown("※メインサーバーの共有フォルダ等のパスを直接入力してください")

if "data_dir" not in st.session_state:
    st.session_state["data_dir"] = DEFAULT_DATA_DIR

if "enable_ai" not in st.session_state:
    st.session_state["enable_ai"] = ENABLE_AI_DEFAULT

data_dir_input = st.sidebar.text_input("データ保存先パス", st.session_state["data_dir"])
st.session_state["data_dir"] = data_dir_input

# AI機能のON/OFFスイッチ
st.sidebar.toggle("AI機能（自動解析・チャット）を使用する", key="enable_ai")

# --- デバッグ・診断機能 ---
st.sidebar.divider()
st.sidebar.subheader("🧰 接続診断")
current_path = Path(st.session_state["data_dir"])

if current_path.exists():
    st.sidebar.success("✅ 接続成功")
    # DBのレコード数を確認
    try:
        conn = get_db_connection()
        count = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        st.sidebar.caption(f"データベース内に {count} 件の記録を確認")
        conn.close()
    except:
        st.sidebar.caption("DB確認エラー")
else:
    st.sidebar.error("❌ 接続失敗 (パスが見つかりません)")
    st.sidebar.caption("ネットワーク設定やアクセス権限を確認してください")

if st.sidebar.button("設定をデフォルトに戻す"):
    st.session_state["data_dir"] = DEFAULT_DATA_DIR
    st.rerun()

# --- AIサーバー接続診断 ---
if st.session_state.get("enable_ai", True):
    st.sidebar.divider()
    st.sidebar.subheader("🤖 AI接続診断")
    from config import AI_BASE_URL
    import requests
    try:
        # modelsエンドポイントで死活監視
        api_url = f"{AI_BASE_URL}/models"
        response = requests.get(api_url, timeout=2)
        if response.status_code == 200:
            st.sidebar.success("AIサーバー接続中")
        else:
            st.sidebar.warning(f"AIサーバー応答異常 ({response.status_code})")
    except Exception:
        st.sidebar.error("AIサーバー未起動")
        st.sidebar.caption("サーバーPCで LLM を起動してください")


# ==========================================
# メインメニュー
# ==========================================
st.sidebar.title("メニュー")

# ONになっている機能だけでメニューを作成
menu_options = []
if ENABLE_REGISTRATION: menu_options.append("登録")
if ENABLE_MINUTES:      menu_options.append("議事録作成")
if st.session_state.get("enable_ai", True): menu_options.append("AI相談")
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
elif menu == "AI相談":
    show_ai_chat()
elif menu == "検索":
    show_search()
