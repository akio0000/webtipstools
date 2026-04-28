import streamlit as st
import json
import requests
from pathlib import Path
from openai import OpenAI
from utils import get_db_connection
from config import DEFAULT_DATA_DIR, AI_BASE_URL, AI_API_KEY, AI_MODEL

import base64
from PIL import Image
import io

# ==========================================
# 設定: Llama-server
# ==========================================
client = OpenAI(base_url=AI_BASE_URL, api_key=AI_API_KEY)

def image_to_base64(image_path):
    """画像を512x512程度にリサイズしてからBase64形式に変換する（VRAM節約）"""
    with Image.open(image_path) as img:
        # アスペクト比を維持してリサイズ
        img.thumbnail((448, 448)) # 多くのマルチモーダルモデルの標準サイズに合わせる
        buffered = io.BytesIO()
        # フォーマットを統一して保存
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

def analyze_image(image_path, model=AI_MODEL):
    """AIに画像を解析させる（マルチモーダル機能）"""
    try:
        base64_image = image_to_base64(image_path)
        # 画像とテキストの順序を入れ替えたり、フォーマットを微調整
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                        {"type": "text", "text": "こちらの画像の内容を詳しく、日本語で説明してください。"},
                    ],
                }
            ],
            max_tokens=1200,
        )

        # 通常の回答、または思考プロセス（reasoning_content）を取得
        res_text = getattr(response.choices[0].message, 'content', "")
        reasoning = getattr(response.choices[0].message, 'reasoning_content', None)
        
        # 思考プロセスがあるが回答が空、または不十分な場合に統合して返す
        if reasoning and (not res_text or len(res_text) < 10):
            return f"【AIの解析思考】\n{reasoning}\n\n【最終回答】\n{res_text}"
        
        return res_text if res_text else "AIからの応答が空でした。モデルの設定を確認してください。"
    except Exception as e:
        return f"画像解析エラー: {e}"

def get_ai_response(messages, model=AI_MODEL):
    """Llama-server にリクエストを送る"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AIとの通信に失敗しました: {e}"

def extract_keywords_by_ai(query):
    """AIを使って質問文から検索用キーワードを抽出する"""
    messages = [
        {"role": "system", "content": "与えられた文章から、データベース検索に適した重要なキーワード（名詞や型番など）をスペース区切りで抽出してください。余計な説明は不要です。"},
        {"role": "user", "content": f"文章: {query}"}
    ]
    try:
        response = get_ai_response(messages)
        # AIが「キーワード: A B C」のように返す場合もあるので、クリーニング
        words = response.replace("キーワード", "").replace(":", "").replace("：", "").replace("\n", " ")
        return [w.strip() for w in words.split(" ") if len(w.strip()) >= 1]
    except:
        return [query] # 失敗した場合は元の文を返す

def search_context(query, data_folder):
    """
    ユーザーのクエリに関連しそうな情報をデータベースから抽出する。
    """
    # 1. AIに頼んで重要な単語を抜き出す
    keywords = extract_keywords_by_ai(query)
    
    # 2. 簡易クリーニングによる予備キーワード
    clean_query = query.replace("について", "").replace("とは", "").replace("教えて", "").replace("か", " ")
    for p in ["何か", "書かれてる", "どこ", "どこに", "あります", "？", "。"]:
        clean_query = clean_query.replace(p, " ")
    backup_keywords = [q.strip() for q in clean_query.replace("　", " ").split(" ") if len(q.strip()) >= 1]
    
    all_keywords = list(dict.fromkeys(keywords + backup_keywords))
    
    # 3. データベース検索
    conn = get_db_connection()
    try:
        related_entries = []
        # 全データを取得（スコアリングのため）
        # ※データが極端に多い場合は、SQLの段階でキーワードマッチさせるほうが良いが、
        #   ここでは柔軟なスコアリングのため一旦取得してメモリ内で処理する。
        rows = conn.execute("SELECT * FROM records").fetchall()
        
        for row in rows:
            entry = dict(row)
            score = 0
            # 検索対象を統合
            searchable_text = f"{entry['title']} {entry['content']} {entry['tags']} {entry['details']}".lower()
            
            for kw in all_keywords:
                if kw.lower() in searchable_text:
                    if kw.lower() in entry['title'].lower():
                        score += 5
                    else:
                        score += 1
            
            if score > 0:
                # search.py と同様のデコード
                entry["text"] = entry.pop("content")
                entry["tags"] = entry["tags"].split(",") if entry["tags"] else []
                entry["file_path"] = json.loads(entry["file_path"])
                entry["details"] = json.loads(entry["details"])
                related_entries.append((score, entry))
                
        related_entries.sort(key=lambda x: x[0], reverse=True)
        return [e[1] for e in related_entries[:5]]
    finally:
        conn.close()

def show_ai_chat():
    st.header("AI 相談ツール")
    st.markdown("登録された記録（ナレッジベース）に基づいて AI が回答します。")

    data_dir_path = st.session_state.get("data_dir", DEFAULT_DATA_DIR)
    data_dir = Path(data_dir_path)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # チャット履歴の表示
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザー入力
    if prompt := st.chat_input("何を知りたいですか？"):
        # ユーザーのメッセージを表示
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 関連情報の検索
        with st.status("ナレッジベースを検索中...", expanded=False) as status:
            context_entries = search_context(prompt, data_dir)
            if context_entries:
                st.write(f"{len(context_entries)} 件の参考情報が見つかりました。")
                context_texts = []
                for entry in context_entries:
                    context_texts.append(f"【タイトル: {entry.get('title')}】\n{entry.get('text')}")
                context_str = "\n\n".join(context_texts)
                status.update(label="検索完了。AIが回答を生成しています...", state="complete")
            else:
                st.write("関連する情報が見つかりませんでした。一般的な知識で回答します。")
                context_str = "参考となる情報は見つかりませんでした。"
                status.update(label="検索完了（関連情報なし）", state="complete")

        # プロンプトの組み立て
        system_prompt = (
            "あなたは社内のナレッジベースに基づいて質問に答えるアシスタントです。\n"
            "与えられた【参考情報】の中に答えがある場合は、それに基づいて答えてください。\n"
            "答えがない、または不足している場合は、その旨を伝えた上で一般的な知識で補足してください。\n\n"
            f"【参考情報】\n{context_str}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]
        # 直近の履歴も追加（3往復分）
        messages.extend(st.session_state.chat_history[-6:])

        # AI の回答
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = get_ai_response(messages)
            response_placeholder.markdown(full_response)
        
        st.session_state.chat_history.append({"role": "assistant", "content": full_response})
