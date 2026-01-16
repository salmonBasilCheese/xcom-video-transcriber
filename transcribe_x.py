import os
import sys
import subprocess
import glob
from dotenv import load_dotenv
from openai import OpenAI  # 新しい書き方
import yt_dlp

# 環境設定の読み込み
load_dotenv()
# 新しいクライアント初期化方法
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==========================================
# 設定
# ==========================================
TEST_MODE = False  # ★まずはTrueのまま（3分テスト）
CHUNK_TIME = 900  # 15分分割
# ==========================================

def download_audio(url, output_filename="downloaded_audio"):
    """yt-dlpを使って音声をダウンロード"""
    print(f"Downloading from {url}...")
    
    # 既存削除
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
        'quiet': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return f"{output_filename}.mp3"
    except Exception as e:
        print(f"Error downloading: {e}")
        return None

def split_audio_ffmpeg(input_file, segment_time=900):
    """FFmpegで分割"""
    print(f"Splitting audio into {segment_time}s chunks...")
    
    output_pattern = "chunk_%03d.mp3"
    for f in glob.glob("chunk_*.mp3"):
        os.remove(f)

    if TEST_MODE:
        print("★ TEST MODE: Processing only the first 3 minutes (180s) ★")
        cmd = [
            "ffmpeg", "-i", input_file,
            "-t", "180",
            "-c", "copy", "chunk_000.mp3", "-y"
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ["chunk_000.mp3"]

    cmd = [
        "ffmpeg", "-i", input_file,
        "-f", "segment", "-segment_time", str(segment_time),
        "-c", "copy", output_pattern, "-y"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return sorted(glob.glob("chunk_*.mp3"))

def transcribe_chunk(file_path):
    """Whisper API (新しい書き方)"""
    print(f"Transcribing {file_path}...")
    try:
        with open(file_path, "rb") as audio_file:
            # ここが変わりました
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )
        return transcript
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

def translate_text(text):
    """GPT-4o-mini (新しい書き方)"""
    try:
        # ここが変わりました
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional translator. Translate the following English text into natural Japanese."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"(Translation Error: {e})"

def main():
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Please enter the X.com video URL: ").strip()

    if not url:
        print("URL is required.")
        return

    # ダウンロード処理は既にファイルがあればスキップする簡易ロジックを追加してもよいが
    # ここでは毎回クリーンに実行します
    audio_file = download_audio(url)
    if not audio_file: return

    chunks = split_audio_ffmpeg(audio_file, CHUNK_TIME)
    output_md = "transcript.md"
    
    with open(output_md, "w", encoding="utf-8") as f:
        f.write(f"# Transcription for {url}\n\n")

    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}...")
        
        result = transcribe_chunk(chunk)
        if not result: continue

        # 新しいライブラリはオブジェクトで返ってくるため .segments でアクセス
        segments = result.segments 
        
        with open(output_md, "a", encoding="utf-8") as f:
            for segment in segments:
                # オブジェクト属性アクセスに変更
                start = segment.start
                end = segment.end
                text = segment.text
                
                offset = i * CHUNK_TIME
                def fmt_time(seconds):
                    h = int(seconds // 3600)
                    m = int((seconds % 3600) // 60)
                    s = int(seconds % 60)
                    return f"{h:02}:{m:02}:{s:02}"

                time_str = f"[{fmt_time(start + offset)} - {fmt_time(end + offset)}]"
                jp_text = translate_text(text)
                
                # 画面に表示
                print(f"{time_str} EN: {text[:20]}... -> JP: {jp_text[:20]}...")
                
                # ファイルに保存
                f.write(f"### {time_str}\n")
                f.write(f"**EN:** {text}\n")
                f.write(f"**JP:** {jp_text}\n\n")

    print(f"\nDone! Check the file: {output_md}")

if __name__ == "__main__":
    main()