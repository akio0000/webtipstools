import json
import sqlite3
from pathlib import Path
from datetime import datetime
from config import DB_PATH

# ==========================================
# データベース初期化・接続
# ==========================================
def get_db_connection():
    """データベース接続を取得し、テーブルを初期化する。起動時にバックアップも作成する。"""
    # フォルダの作成
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # --- 自動バックアップ機能 ---
    if DB_PATH.exists():
        try:
            backup_dir = DB_PATH.parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"webtips_{timestamp}.db"
            
            import shutil
            shutil.copy2(str(DB_PATH), str(backup_path))
            
            # 古いバックアップの整理（最新10件のみ保持）
            backups = sorted(list(backup_dir.glob("webtips_*.db")), key=lambda x: x.stat().st_mtime)
            while len(backups) > 10:
                backups.pop(0).unlink()
        except Exception as e:
            print(f"バックアップ作成エラー: {e}")

    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row # カラム名でアクセスできるようにする
    
    # テーブル作成
    conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            title TEXT,
            content TEXT,
            tags TEXT,
            url TEXT,
            file_path TEXT,
            created_at TEXT,
            details TEXT
        )
    """)
    conn.commit()
    return conn

# ==========================================
# データの保存・更新・削除
# ==========================================
def check_if_record_exists(source, title, content):
    """同一のソース、タイトル、内容を持つレコードが既に存在するか確認する"""
    conn = get_db_connection()
    try:
        query = "SELECT id FROM records WHERE source = ? AND title = ? AND content = ?"
        result = conn.execute(query, (source, title, content)).fetchone()
        return result is not None
    finally:
        conn.close()

def save_record_to_db(entry):
    """レコードをデータベースに保存する"""
    conn = get_db_connection()
    try:
        # データの整理
        tags_str = ",".join(entry.get("tags", []))
        file_path_json = json.dumps(entry.get("file_path", []))
        details_json = json.dumps(entry.get("details", {}), ensure_ascii=False)
        
        conn.execute("""
            INSERT INTO records (source, title, content, tags, url, file_path, created_at, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.get("source", "mobile"),
            entry.get("title", ""),
            entry.get("text", ""),
            tags_str,
            entry.get("url", ""),
            file_path_json,
            entry.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            details_json
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB保存エラー: {e}")
        return False
    finally:
        conn.close()

def update_record_in_db(record_id, updated_fields):
    """データベースのレコードを更新する"""
    conn = get_db_connection()
    try:
        if "tags" in updated_fields:
            updated_fields["tags"] = ",".join(updated_fields["tags"])
        if "file_path" in updated_fields:
            updated_fields["file_path"] = json.dumps(updated_fields["file_path"])
        if "details" in updated_fields:
            updated_fields["details"] = json.dumps(updated_fields["details"], ensure_ascii=False)
        if "text" in updated_fields:
            updated_fields["content"] = updated_fields.pop("text")

        set_clause = ", ".join([f"{k} = ?" for k in updated_fields.keys()])
        params = list(updated_fields.values())
        params.append(record_id)
        
        conn.execute(f"UPDATE records SET {set_clause} WHERE id = ?", params)
        conn.commit()
        return True
    except Exception as e:
        print(f"DB更新エラー: {e}")
        return False
    finally:
        conn.close()

def delete_record_from_db(record_id):
    """レコードをデータベースから削除する（ファイルは安全のため削除しません）"""
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB削除エラー: {e}")
        return False
    finally:
        conn.close()

# ==========================================
# 既存タグ・参加者の収集 (DB版)
# ==========================================
def collect_existing_tags(data_folder=None):
    """データベースから使用済みタグを集める"""
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT tags FROM records").fetchall()
        all_tags = set()
        for row in rows:
            if row["tags"]:
                for t in row["tags"].split(","):
                    if t.strip():
                        all_tags.add(t.strip())
        return sorted(list(all_tags))
    finally:
        conn.close()

def collect_existing_participants(data_folder=None):
    """データベースのdetails内から参加者名を集める"""
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT details FROM records").fetchall()
        all_participants = set()
        import re
        for row in rows:
            details = json.loads(row["details"])
            p_str = details.get("参加者", "")
            if p_str:
                names = re.split(r'[,\n、，\s]+', p_str)
                for n in names:
                    if n.strip():
                        all_participants.add(n.strip())
        return sorted(list(all_participants))
    finally:
        conn.close()

# ==========================================
# 動画処理 (FFmpeg使用)
# ==========================================
def compress_video(input_path, output_path):
    """FFmpegを使用して動画をリサイズ・圧縮する"""
    import subprocess
    command = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", "scale='min(1280,iw)':-2",
        "-c:v", "libx264",
        "-crf", "28",
        "-preset", "faster",
        "-c:a", "aac",
        "-b:a", "128k",
        str(output_path)
    ]
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except Exception as e:
        return False, str(e)

# ==========================================
# 初期データ移行 (JSON -> DB)
# ==========================================
def migrate_jsons_to_db(data_dir, reference_dir=None):
    """既存のJSONファイルをDBへ移行する（重複は個別チェック）"""
    # フォルダが存在しない場合は作成
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    if reference_dir:
        reference_dir = Path(reference_dir)

    def process_file(json_file, source_name):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list): return
                
                for entry in data:
                    # 形式の変換（マッピング）
                    title = entry.get("title", "")
                    content = entry.get("text", "")
                    tags = entry.get("tags", [])
                    file_path = entry.get("file_path", [])
                    if isinstance(file_path, str):
                        file_path = [file_path] if file_path else []
                    
                    created_at = entry.get("created_at", entry.get("date", ""))
                    if "date" in entry and "time" in entry:
                        created_at = f"{entry['date']} {entry['time']}"
                    
                    # 参考データなどタイトルがない場合
                    if not title and content:
                        title = content.splitlines()[0][:30] # 最初の1行をタイトルに
                    
                    # 重複チェック（同一ソース、タイトル、内容）
                    if check_if_record_exists(source_name, title, content):
                        continue

                    # 固有フィールド（detailsへ）
                    details = {}
                    exclude = ["title", "text", "tags", "file_path", "created_at", "date", "time", "url"]
                    for k, v in entry.items():
                        if k not in exclude:
                            details[k] = v
                    
                    save_record_to_db({
                        "source": source_name,
                        "title": title,
                        "text": content,
                        "tags": tags,
                        "url": entry.get("url", ""),
                        "file_path": file_path,
                        "created_at": created_at,
                        "details": details
                    })
        except Exception as e:
            print(f"移行エラー ({json_file.name}): {e}")

    # 通常データの移行
    for jf in data_dir.glob("*.json"):
        source = "mobile"
        if "minutes" in jf.name: source = "minutes"
        process_file(jf, source)
    
    # 参考データの移行
    if reference_dir and reference_dir.exists():
        for jf in reference_dir.glob("*.json"):
            process_file(jf, "reference")

# 互換性のためのダミー
def load_data(f): return []
def save_data(f, d): pass
