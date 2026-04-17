import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from register import load_data, save_data, collect_existing_tags

def show_minutes_registration():
    st.title("議事録の作成")
    st.markdown("会議の内容を入力して保存します。")

    # 保存先設定
    data_dir_path = st.session_state.get("data_dir", r"C:\Users\user\Desktop\webapp_env\data")
    data_dir = Path(data_dir_path)
    image_dir = data_dir / "images"
    json_file = data_dir / "minutes_records.json"

    try:
        image_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        st.error(f"保存先フォルダを作成できませんでした: {e}")
        return

    # ==========================================
    # 入力フォーム（全項目表示）
    # ==========================================
    default_title = f"{datetime.now().strftime('%Y%m%d')}_定例会議"
    title = st.text_input("タイトル（会議名など）", value=default_title)

    st.divider()
    
    # 日時
    col_d, col_t = st.columns(2)
    with col_d:
        d = st.date_input("日付", value=datetime.now())
    with col_t:
        t = st.time_input("開始時間", value=datetime.now())
    
    # 各項目
    location = st.text_input("場所", placeholder="会議室A、オンライン等")
    participants = st.text_area("参加者", placeholder="出席者氏名、部署名など")
    agenda = st.text_area("議題", placeholder="1. ○○について\n2. △△の進捗", height=100)
    content = st.text_area("内容（詳細）", height=250)
    remarks = st.text_area("備考", height=100)
    next_schedule = st.text_input("次回予定", placeholder="202X/XX/XX XX:XX～")
    
    url_input = st.text_input("関連URL (Web会議や参考資料)")

    # ==========================================
    # タグ・ファイル
    # ==========================================
    st.divider()
    existing_tags = collect_existing_tags(data_dir)
    st.markdown("**タグ**")
    selected_tags = st.multiselect("既存タグから選択", options=existing_tags, default=[t for t in ["議事録"] if t in existing_tags])
    new_tags_input = st.text_input("新しいタグを追加", value="" if "議事録" in (existing_tags + selected_tags) else "議事録")
    uploaded_files = st.file_uploader("添付ファイル", type=["jpg", "jpeg", "png", "pdf", "csv", "xlsx", "txt", "bat", "url"], accept_multiple_files=True)

    # ==========================================
    # 保存処理
    # ==========================================
    if st.button("議事録を保存"):
        if not title:
            st.warning("タイトルは必須項目です。")
            return

        # フィールドの整理
        fields = {
            "日時": f"{d} {t.strftime('%H:%M')}",
            "場所": location,
            "参加者": participants,
            "議題": agenda,
            "内容": content,
            "備考": remarks,
            "次回予定": next_schedule
        }

        # 表示用・検索用にテキストをまとめる（空でない項目のみ）
        content_lines = []
        structured_data = {}
        for k, v in fields.items():
            val = str(v).strip()
            if val:
                content_lines.append(f"【{k}】\n{val}\n")
                structured_data[k] = val

        full_text = "\n".join(content_lines)

        # タグ処理
        new_processed = new_tags_input.strip().replace("　", ",").replace(" ", ",").replace("、", ",").replace("，", ",")
        new_tags = [t.strip() for t in new_processed.split(",") if t.strip()]
        tags = list(dict.fromkeys(selected_tags + new_tags))

        # ファイル保存
        file_paths = []
        if uploaded_files:
            for i, uploaded_file in enumerate(uploaded_files):
                timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"{timestamp_str}_{i}_{uploaded_file.name}"
                image_path = image_dir / filename
                try:
                    with image_path.open("wb") as f: f.write(uploaded_file.getbuffer())
                    file_paths.append(str(image_path).replace("\\", "/"))
                except: st.error(f"保存失敗: {uploaded_file.name}")

        # JSON保存
        now = datetime.now()
        entry = {
            "title": title,
            "url": url_input,
            "text": full_text,
            "details": structured_data,
            "tags": tags,
            "file_path": file_paths,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            data = load_data(json_file)
            data.append(entry)
            save_data(json_file, data)
            st.success(f"議事録（{json_file.name}）を正常に保存しました！")
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
