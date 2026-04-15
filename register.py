import streamlit as st
import json
from pathlib import Path
from datetime import datetime

# ==========================================
# JSON 読み書き
# ==========================================
def load_data(json_file):
    if not json_file.exists() or json_file.stat().st_size == 0:
        return []
    try:
        with json_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_data(json_file, data):
    with json_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==========================================
# 既存タグの収集（サジェスト用）
# ==========================================
def collect_existing_tags(data_folder):
    """データフォルダ内の全JSONから使用済みタグを集める"""
    all_tags = set()
    if not data_folder.exists():
        return sorted(all_tags)

    for json_file in data_folder.glob("*.json"):
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                for entry in data:
                    for tag in entry.get("tags", []):
                        if tag.strip():
                            all_tags.add(tag.strip())
        except:
            pass

    return sorted(all_tags)

# ==========================================
# Streamlit UI
# ==========================================
def show_registration():
    st.title("登録")

    # メインサーバー/保存先設定の取得
    data_dir_path = st.session_state.get("data_dir", r"C:\Users\user\Desktop\data")
    data_dir = Path(data_dir_path)
    image_dir = data_dir / "images"
    json_file = data_dir / "mobile_records.json"

    # フォルダの自動作成
    try:
        image_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        st.error(f"保存先フォルダを作成できませんでした。パスを確認してください: {e}")
        return

    # 入力フォーム
    uploaded_file = st.file_uploader("ファイルのアップロード", type=["jpg", "jpeg", "png", "pdf", "csv", "xlsx"])
    title = st.text_input("タイトル")
    content = st.text_area("内容")

    # ==========================================
    # タグ入力（サジェスト機能付き）
    # ==========================================
    existing_tags = collect_existing_tags(data_dir)

    st.markdown("**タグ**")
    if existing_tags:
        selected_tags = st.multiselect(
            "過去に使用したタグから選択（複数選択可）",
            options=existing_tags
        )
    else:
        selected_tags = []
        st.caption("まだタグの履歴がありません")

    new_tags_input = st.text_input("新しいタグを追加（カンマ区切りで入力）")

    # ==========================================
    # 保存処理
    # ==========================================
    if st.button("保存"):
        if not title or not content:
            st.warning("タイトルと内容は必須項目です。")
            return

        # タグ処理（選択タグ + 新規入力タグを統合）
        new_processed = (
            new_tags_input.strip()
            .replace("　", ",")
            .replace(" ", ",")
            .replace("、", ",")
            .replace("，", ",")
        )
        new_tags = [t.strip() for t in new_processed.split(",") if t.strip()]

        # 重複を除いて統合
        tags = list(dict.fromkeys(selected_tags + new_tags))

        # ==========================================
        # ファイルの保存
        # ==========================================
        file_path_str = ""
        if uploaded_file:
            timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
            ext = Path(uploaded_file.name).suffix

            # 安全なファイル名を作成
            safe_title = title.replace("\\", "_").replace("/", "_").replace(":", "_").replace("*", "_")
            safe_title = safe_title.replace("?", "_").replace("\"", "_").replace("<", "_").replace(">", "_").replace("|", "_")
            filename = f"{timestamp_str}_{safe_title}{ext}"

            image_path = image_dir / filename

            try:
                with image_path.open("wb") as f:
                    f.write(uploaded_file.getbuffer())
                file_path_str = str(image_path).replace("\\", "/")
            except Exception as e:
                st.error(f"ファイルの保存時にエラーが発生しました: {e}")
                return

        # ==========================================
        # データ（JSON）保存
        # ==========================================
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        entry = {
            "title": title,
            "text": content,
            "tags": tags,
            "file_path": file_path_str,
            "date": date_str,
            "time": time_str,
            "created_at": timestamp
        }

        try:
            data = load_data(json_file)
            data.append(entry)
            save_data(json_file, data)

            st.success("正常に登録されました！")
            if file_path_str:
                if file_path_str.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                    st.image(file_path_str, caption="アップロードされたファイル", use_column_width=True)
                else:
                    st.info(f"ファイルを保存しました: {filename}")

        except Exception as e:
            st.error(f"データの保存時にエラーが発生しました: {e}")
