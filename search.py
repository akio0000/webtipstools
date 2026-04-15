import json
from pathlib import Path
import streamlit as st
import base64
import pandas as pd

# ==========================================
# JSON 読み込み（フォルダ内の全 JSON）
# ==========================================
def load_all_data(data_folder):
    if not data_folder.exists():
        return []

    all_data = []

    for json_file in data_folder.glob("*.json"):
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                for i, entry in enumerate(data):
                    entry["_source_file"] = json_file.name
                    entry["_index"] = i
                all_data.extend(data)
        except Exception as e:
            st.error(f"{json_file.name} の読み込みエラー: {e}")

    return all_data

# ==========================================
# 特定JSONファイルの読み書き
# ==========================================
def load_json_file(json_path):
    if not json_path.exists() or json_path.stat().st_size == 0:
        return []
    try:
        with json_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_json_file(json_path, data):
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==========================================
# 検索処理
# ==========================================
def search_entries(conditions, data_folder, mode="or"):
    data = load_all_data(data_folder)

    if not conditions.get("title") and not conditions.get("text") and not conditions.get("tag"):
        return data

    results = []

    for entry in data:
        matches = []

        if conditions.get("title"):
            matches.append(conditions["title"].lower() in entry.get("title", "").lower())

        if conditions.get("text"):
            matches.append(conditions["text"].lower() in entry.get("text", "").lower())

        if conditions.get("tag"):
            target_tags = [t.lower() for t in entry.get("tags", [])]
            search_tag = conditions["tag"].lower()
            matches.append(any(search_tag in t for t in target_tags))

        if mode == "and" and matches and all(matches):
            results.append(entry)
        elif mode == "or" and matches and any(matches):
            results.append(entry)

    return results

# ==========================================
# 既存タグの収集（タグサジェスト用）
# ==========================================
def collect_existing_tags(data_folder):
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
# レコードの削除処理
# ==========================================
def delete_entry(data_folder, source_file, index):
    json_path = data_folder / source_file
    data = load_json_file(json_path)
    if 0 <= index < len(data):
        # 添付ファイルも削除
        file_path = data[index].get("file_path", "")
        if file_path:
            fp = Path(file_path.replace("\\", "/"))
            if fp.is_file():
                try:
                    fp.unlink()
                except:
                    pass
        data.pop(index)
        save_json_file(json_path, data)
        return True
    return False

# ==========================================
# レコードの更新処理
# ==========================================
def update_entry(data_folder, source_file, index, updated_fields):
    json_path = data_folder / source_file
    data = load_json_file(json_path)
    if 0 <= index < len(data):
        data[index].update(updated_fields)
        save_json_file(json_path, data)
        return True
    return False

# ==========================================
# ファイルプレビュー表示
# ==========================================
def show_file_preview(raw_path, unique_key):
    if not raw_path:
        return

    file_path = raw_path.replace("\\", "/")
    file_path_obj = Path(file_path)
    file_name = file_path_obj.name

    if not file_path_obj.exists():
        st.warning(f"添付ファイルが見つかりません: {file_name}")
        return

    # 画像プレビュー
    if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".gif")) and file_path_obj.is_file():
        with st.expander("画像を表示"):
            st.image(file_path, caption=file_name)
        return

    # PDF プレビュー
    if file_path.lower().endswith(".pdf") and file_path_obj.is_file():
        with st.expander("PDFを表示"):
            try:
                with open(file_path_obj, "rb") as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"PDF読み込みエラー: {e}")
        return

    # CSV プレビュー
    if file_path.lower().endswith(".csv") and file_path_obj.is_file():
        with st.expander("CSVを表示"):
            try:
                df = pd.read_csv(file_path_obj, encoding="utf-8")
                st.dataframe(df)
            except Exception as e:
                st.warning(f"CSV読み込みエラー: {e}")
        return

    # Excel プレビュー
    if file_path.lower().endswith(".xlsx") and file_path_obj.is_file():
        with st.expander("Excelを表示"):
            try:
                df = pd.read_excel(file_path_obj)
                st.dataframe(df)
            except Exception as e:
                st.warning(f"Excel読み込みエラー: {e}")
        return

    # その他ファイル → ダウンロード
    if file_path_obj.is_file():
        with st.expander(f"ファイルをダウンロード: {file_name}"):
            try:
                with file_path_obj.open("rb") as f:
                    st.download_button(
                        label="ダウンロード",
                        data=f,
                        file_name=file_name,
                        key=f"dl_{unique_key}"
                    )
            except Exception as e:
                st.warning(f"読み込みエラー: {e}")

# ==========================================
# 結果表示（編集・削除機能付き）
# ==========================================
def display_results(results, data_dir):
    existing_tags = collect_existing_tags(data_dir)

    for i, entry in enumerate(results):
        source_file = entry.get("_source_file", "")
        entry_index = entry.get("_index", -1)
        unique_key = f"{source_file}_{entry_index}_{i}"

        st.markdown("----")

        # 登録日時の表示
        date_str = entry.get('date', '')
        time_str = entry.get('time', '')
        created_at = entry.get('created_at', f"{date_str} {time_str}".strip())

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {entry.get('title', '無題')}")
        with col2:
            st.text(f"登録日時: {created_at}")

        st.markdown(f"**内容:**\n{entry.get('text', '')}")

        tags = entry.get("tags", [])
        if tags:
            st.markdown(f"**タグ:** {', '.join(tags)}")

        # ファイルプレビュー
        show_file_preview(entry.get("file_path", "").strip(), unique_key)

        # ==========================================
        # 編集・削除ボタン
        # ==========================================
        if source_file and entry_index >= 0:
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 6])

            with btn_col1:
                edit_clicked = st.button("✏️ 編集", key=f"edit_{unique_key}")
            with btn_col2:
                delete_clicked = st.button("🗑️ 削除", key=f"delete_{unique_key}")

            # --- 編集モード ---
            edit_state_key = f"editing_{unique_key}"
            if edit_clicked:
                st.session_state[edit_state_key] = True

            if st.session_state.get(edit_state_key, False):
                with st.container():
                    st.markdown("---")
                    st.subheader("記録の編集")

                    new_title = st.text_input("タイトル", value=entry.get("title", ""), key=f"ed_title_{unique_key}")
                    new_text = st.text_area("内容", value=entry.get("text", ""), key=f"ed_text_{unique_key}")

                    # タグ編集（サジェスト付き）
                    current_tags = entry.get("tags", [])
                    # 既存タグと登録済みタグを合わせた候補リスト
                    all_tag_options = sorted(set(existing_tags) | set(current_tags))

                    edited_tags = st.multiselect(
                        "タグを選択（過去の履歴から選べます）",
                        options=all_tag_options,
                        default=current_tags,
                        key=f"ed_tags_{unique_key}"
                    )
                    extra_tags_input = st.text_input(
                        "新しいタグを追加（カンマ区切り）",
                        key=f"ed_newtags_{unique_key}"
                    )

                    save_col, cancel_col, _ = st.columns([1, 1, 6])
                    with save_col:
                        if st.button("💾 保存", key=f"save_{unique_key}"):
                            # 新規タグ処理
                            extra_processed = (
                                extra_tags_input.strip()
                                .replace("　", ",").replace(" ", ",")
                                .replace("、", ",").replace("，", ",")
                            )
                            extra_list = [t.strip() for t in extra_processed.split(",") if t.strip()]
                            final_tags = list(dict.fromkeys(edited_tags + extra_list))

                            updated = {
                                "title": new_title,
                                "text": new_text,
                                "tags": final_tags
                            }
                            if update_entry(data_dir, source_file, entry_index, updated):
                                st.success("更新しました！")
                                st.session_state[edit_state_key] = False
                                # 検索結果をクリアして再検索を促す
                                if "results" in st.session_state:
                                    del st.session_state["results"]
                                st.rerun()
                            else:
                                st.error("更新に失敗しました。")

                    with cancel_col:
                        if st.button("キャンセル", key=f"cancel_{unique_key}"):
                            st.session_state[edit_state_key] = False
                            st.rerun()

            # --- 削除確認 ---
            delete_confirm_key = f"del_confirm_{unique_key}"
            if delete_clicked:
                st.session_state[delete_confirm_key] = True

            if st.session_state.get(delete_confirm_key, False):
                st.warning(f"「{entry.get('title', '無題')}」を本当に削除しますか？（添付ファイルも削除されます）")
                yes_col, no_col, _ = st.columns([1, 1, 6])
                with yes_col:
                    if st.button("はい、削除する", key=f"yes_del_{unique_key}"):
                        if delete_entry(data_dir, source_file, entry_index):
                            st.success("削除しました。")
                            st.session_state[delete_confirm_key] = False
                            if "results" in st.session_state:
                                del st.session_state["results"]
                            st.rerun()
                        else:
                            st.error("削除に失敗しました。")
                with no_col:
                    if st.button("キャンセル", key=f"no_del_{unique_key}"):
                        st.session_state[delete_confirm_key] = False
                        st.rerun()

# ==========================================
# 検索画面 UI
# ==========================================
def show_search():
    st.header("記録の検索")

    data_dir_path = st.session_state.get("data_dir", r"C:\Users\user\Desktop\webapp_env\data")
    data_dir = Path(data_dir_path)

    if not data_dir.exists():
        st.warning(f"データフォルダが存在しません: {data_dir}")
        return

    # タグサジェスト用のタグ一覧を取得
    existing_tags = collect_existing_tags(data_dir)

    with st.form("search_form"):
        title = st.text_input("タイトル")
        text = st.text_input("内容")
        tag = st.text_input("タグ")
        if existing_tags:
            st.caption(f"💡 使用中のタグ: {', '.join(existing_tags)}")
        mode = st.radio("検索モード", ["or", "and"], horizontal=True)
        submitted = st.form_submit_button("検索")

    if submitted:
        conditions = {
            "title": title.strip(),
            "text": text.strip(),
            "tag": tag.strip()
        }
        st.session_state["results"] = search_entries(conditions, data_dir, mode)

    if "results" in st.session_state:
        results = st.session_state["results"]
        st.success(f"{len(results)} 件の記録が見つかりました")
        display_results(results, data_dir)
