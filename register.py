import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from config import DEFAULT_DATA_DIR
from ai_utils import analyze_image

from utils import collect_existing_tags, compress_video, save_record_to_db

# ==========================================
# Streamlit UI
# ==========================================
def show_registration():
    st.title("記録の登録")

    # メインサーバー/保存先設定の取得
    data_dir_path = st.session_state.get("data_dir", DEFAULT_DATA_DIR)
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
    uploaded_files = st.file_uploader("ファイルのアップロード", type=["jpg", "jpeg", "png", "pdf", "csv", "xlsx","txt","bat", "url", "mp4", "mov", "avi", "mkv"],
    accept_multiple_files=True)
    title = st.text_input("タイトル")
    url_input = st.text_input("参考URL (http～)")
    content = st.text_area("内容")
    
    # セッションでAIが有効な場合のみ解析オプションを表示
    if st.session_state.get("enable_ai", True):
        enable_ai_analysis = st.checkbox("AIで画像の内容を自動解析する", value=True)
    else:
        enable_ai_analysis = False
        
    enable_video_compression = st.checkbox("動画を最適化（リサイズ・圧縮）する", value=True, help="動画のサイズを縮小し、再生互換性を高めます（処理に時間がかかる場合があります）")

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
        # 画像等ファイル保存
        # ==========================================
        file_paths = []
        if uploaded_files:
            for i, uploaded_file in enumerate(uploaded_files):
                timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
                ext = Path(uploaded_file.name).suffix

                # 安全なファイル名を作成（スペースや全角スペースも置換）
                safe_title = title.replace("\\", "_").replace("/", "_").replace(":", "_").replace("*", "_")
                safe_title = safe_title.replace("?", "_").replace("\"", "_").replace("<", "_").replace(">", "_").replace("|", "_")
                safe_title = safe_title.replace(" ", "_").replace("　", "_").replace("、", "_").replace("，", "_")
                # 複数ファイルある場合はインデックスを付ける
                filename = f"{timestamp_str}_{safe_title}_{i}{ext}"

                image_path = image_dir / filename

                try:
                    # 動画圧縮の判定
                    is_video = ext.lower() in [".mp4", ".mov", ".avi", ".mkv"]
                    
                    if is_video and enable_video_compression:
                        with st.spinner(f"動画を圧縮中: {uploaded_file.name}..."):
                            # 一時ファイルとして一旦保存
                            temp_path = image_dir / f"temp_{filename}"
                            with temp_path.open("wb") as f:
                                f.write(uploaded_file.getbuffer())
                            
                            # 出力ファイル名は拡張子を .mp4 に統一（互換性のため）
                            if ext.lower() != ".mp4":
                                filename = filename.rsplit(".", 1)[0] + ".mp4"
                                image_path = image_dir / filename

                            success, err_msg = compress_video(temp_path, image_path)
                            
                            # 一時ファイルを削除
                            if temp_path.exists():
                                temp_path.unlink()
                            
                            if not success:
                                st.error(f"動画の圧縮に失敗しました。元のファイル形式で保存します。 Error: {err_msg}")
                                with image_path.open("wb") as f:
                                    f.write(uploaded_file.getbuffer())
                    else:
                        with image_path.open("wb") as f:
                            f.write(uploaded_file.getbuffer())
                    
                    file_paths.append(str(image_path).replace("\\", "/"))
                except Exception as e:
                    st.error(f"ファイルの保存時にエラーが発生しました ({uploaded_file.name}): {e}")
                    # 一部失敗しても続行するか検討が必要だが、ここでは一旦エラー表示
            
        # --- AIによる画像解析 ---
        if enable_ai_analysis and file_paths:
            with st.status("AIが画像を解析中...") as status:
                analysis_results = []
                for path in file_paths:
                    # 画像ファイルのみ解析対象
                    if path.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                        st.write(f"解析中: {Path(path).name}...")
                        result = analyze_image(path)
                        analysis_results.append(f"【画像解析結果: {Path(path).name}】\n{result}")
                
                if analysis_results:
                    ai_summary = "\n\n".join(analysis_results)
                    content = content + "\n\n" + ai_summary
                    status.update(label="画像解析完了！", state="complete")
                else:
                    status.update(label="画像解析対象がありませんでした", state="complete")
            
            # --- 解析結果をステータス枠の外に表示 ---
            if 'ai_summary' in locals() and ai_summary:
                st.info("🤖 **AIによる画像解析結果:**")
                st.markdown(ai_summary)

        # ==========================================
        # データ（JSON）保存
        # ==========================================
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        entry = {
            "title": title,
            "url": url_input,
            "text": content,
            "tags": tags,
            "file_path": file_paths, # リストとして保存
            "date": date_str,
            "time": time_str,
            "created_at": timestamp
        }

        try:
            entry["source"] = "mobile" # 明示的に指定
            if save_record_to_db(entry):
                st.success("正常にデータベースへ登録されました！")
                st.balloons()
                
                # --- おまじない(後片付け) ---
                if st.button("続けて別の記録を登録する"):
                    st.rerun()

                if file_paths:
                    st.divider()
                    st.info(f"{len(file_paths)}件のファイルを保存しました。")
                    for path in file_paths:
                        st.write(Path(path).name)
                        # 画像プレビュー
                        if path.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                            st.image(path, caption=Path(path).name, width=300)
            else:
                st.error("データベースへの保存に失敗しました。")

        except Exception as e:
            st.error(f"データの保存時にエラーが発生しました: {e}")
