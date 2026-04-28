from pathlib import Path

# ==========================================
# 保存先設定
# ==========================================
# デフォルトの保存先パス。ここを書き換えるだけでアプリ全体に反映されます。
DEFAULT_DATA_DIR = r"path to records"

# ==========================================
# AI (Llama-server) 設定
# ==========================================
AI_BASE_URL = "http://localhost:1234/v1"
AI_API_KEY = "lm-studio" #Llama.cppでもOllamaでも
AI_MODEL = "local-model"  # 必要に応じてモデル名を指定

# データベース設定
DB_PATH = Path(DEFAULT_DATA_DIR) / "webtips.db"

# 参考用JSONの読み込み元フォルダ Pathの変更でどこでもドアになる
REFERENCE_JSON_DIR = Path(__file__).parent / "参考json"
