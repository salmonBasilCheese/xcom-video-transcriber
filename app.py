import streamlit as st
import os
import glob
import subprocess
from dotenv import load_dotenv
from openai import OpenAI
import yt_dlp
import re

# ==========================================
# 1. 初期設定と環境変数の読み込み
# ==========================================
st.set_page_config(page_title="X Video Transcriber", layout="wide")
load_dotenv()

# APIキーの確認
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("⚠️ OPENAI_API_KEY が見つかりません。.envファイルを確認してください。")
    st.stop()

client = OpenAI(api_key=api_key)

# ==========================================
# 2. 関数定義（UI向けに調整）
# ==========================================

def download_audio(url):
    """yt-dlpを使って音声をダウンロード"""
    output_filename = "downloaded_audio"
    
    # 既存ファイルの削除
    if os.path.exists(f"{output_filename}.mp3"):
        os.remove(f"{output_filename}.mp3")

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_filename,
        'quiet': True, # ログを抑制
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return f"{output_filename}.mp3"
    except Exception as e:
        st.error(f"ダウンロードエラー: {e}")
        return None

def split_audio_ffmpeg(input_file, segment_time=900, is_test_mode=False):
    """FFmpegで分割"""
    # 古いチャンクファイルを削除
    for f in glob.glob("chunk_*.mp3"):
        os.remove(f)

    if is_test_mode:
        # テストモード: 最初の3分だけ切り出す
        cmd = [
            "ffmpeg", "-i", input_file,
            "-t", "180",
            "-c", "copy", "chunk_000.mp3", "-y"
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ["chunk_000.mp3"]
    else:
        # 通常モード: 全体を分割
        output_pattern = "chunk_%03d.mp3"
        cmd = [
            "ffmpeg", "-i", input_file,
            "-f", "segment", "-segment_time", str(segment_time),
            "-c", "copy", output_pattern, "-y"
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return sorted(glob.glob("chunk_*.mp3"))

def transcribe_chunk(file_path):
    """Whisper APIで文字起こし"""
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )
        return transcript
    except Exception as e:
        st.error(f"文字起こしエラー ({file_path}): {e}")
        return None

def translate_text(text):
    """GPT-4o-miniで翻訳"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional translator. Translate the following English text into natural Japanese."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"(翻訳エラー: {e})"

def create_srt_content(md_lines):
    """Markdownの内容からSRT形式の文字列を作成"""
    srt_content = ""
    counter = 1
    current_time = ""
    time_pattern = re.compile(r"\[(\d{2}:\d{2}:\d{2}) - (\d{2}:\d{2}:\d{2})\]")

    for line in md_lines:
        line = line.strip()
        if line.startswith("###"):
            match = time_pattern.search(line)
            if match:
                start = match.group(1).replace(".", ",") + ",000"
                end = match.group(2).replace(".", ",") + ",000"
                current_time = f"{start} --> {end}"
        elif line.startswith("**JP:**"):
            jp_text = line.replace("**JP:**", "").strip()
            if current_time and jp_text:
                srt_content += f"{counter}\n{current_time}\n{jp_text}\n\n"
                counter += 1
                current_time = "" 
    return srt_content

# ==========================================
# 3. メインアプリ画面 (UI構築)
# ==========================================

st.title("🎥 X Video AI Transcriber & Translator")
st.markdown("X.comの動画URLを入力すると、**文字起こし・翻訳・字幕作成**を全自動で行います。")

# 入力フォーム
with st.form("input_form"):
    url = st.text_input("動画URL (X.com)", placeholder="https://x.com/...")
    is_test_mode = st.checkbox("テストモード (最初の3分間のみ処理)", value=True)
    submitted = st.form_submit_button("実行開始")

# 実行ロジック
if submitted and url:
    # 状態を表示するコンテナ
    status_container = st.status("🚀 処理を開始しました...", expanded=True)
    
    try:
        # --- Step 1: ダウンロード ---
        status_container.write("📥 動画の音声をダウンロード中...")
        audio_file = download_audio(url)
        
        if audio_file:
            status_container.write("✅ ダウンロード完了")
            
            # --- Step 2: 分割 ---
            status_container.write("✂️ 音声を分割中...")
            chunks = split_audio_ffmpeg(audio_file, segment_time=900, is_test_mode=is_test_mode)
            status_container.write(f"✅ {len(chunks)}個のファイルに分割しました")

            # --- Step 3: 文字起こし & 翻訳ループ ---
            status_container.write("🤖 文字起こしと翻訳を実行中...")
            
            output_md_lines = [] # 結果を保存するリスト
            progress_bar = status_container.progress(0)
            
            for i, chunk in enumerate(chunks):
                # 文字起こし
                result = transcribe_chunk(chunk)
                if not result: continue
                
                # 翻訳と整形
                segments = result.segments
                offset = i * 900 # 時間のズレ補正

                for segment in segments:
                    start = segment.start + offset
                    end = segment.end + offset
                    text = segment.text
                    
                    # 時間フォーマット関数
                    def fmt_time(seconds):
                        h = int(seconds // 3600)
                        m = int((seconds % 3600) // 60)
                        s = int(seconds % 60)
                        return f"{h:02}:{m:02}:{s:02}"
                    
                    time_str = f"[{fmt_time(start)} - {fmt_time(end)}]"
                    jp_text = translate_text(text)
                    
                    # リストに保存（後でSRT変換に使う）
                    line_block = [
                        f"### {time_str}",
                        f"**EN:** {text}",
                        f"**JP:** {jp_text}",
                        ""
                    ]
                    output_md_lines.extend(line_block)
                    
                    # リアルタイムで画面に少し表示（ログとして）
                    st.text(f"{time_str} {jp_text[:30]}...")

                # プログレスバー更新
                progress_bar.progress((i + 1) / len(chunks))

            status_container.write("✅ AI処理完了")

            # --- Step 4: ファイル生成 ---
            # MDファイルの中身を作成
            full_md_text = f"# Transcription for {url}\n\n" + "\n".join(output_md_lines)
            
            # SRTファイルの中身を作成
            full_srt_text = create_srt_content(output_md_lines)

            status_container.update(label="🎉 すべて完了しました！", state="complete", expanded=False)

            # --- Step 5: 結果表示とダウンロード ---
            st.success("処理が完了しました。以下のボタンからダウンロードできます。")
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📄 字幕ファイル (.srt) をDL",
                    data=full_srt_text,
                    file_name="japanese.srt",
                    mime="text/plain"
                )
            with col2:
                st.download_button(
                    label="📝 原稿ファイル (.md) をDL",
                    data=full_md_text,
                    file_name="transcript.md",
                    mime="text/markdown"
                )

            # 画面上で確認できるように展開表示
            with st.expander("字幕の内容をプレビュー"):
                st.text(full_srt_text)

    except Exception as e:
        status_container.update(label="❌ エラーが発生しました", state="error")
        st.error(f"予期せぬエラー: {e}")

elif submitted and not url:
    st.warning("URLを入力してください。")