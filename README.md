# X-Video Translator

X.com (旧Twitter) の英語動画を、日本語字幕付きで視聴するためのPythonツールセットです。
動画の音声抽出、AIによる高精度な文字起こし・翻訳、そして字幕ファイル(.srt)の生成までを自動化します。

## 🌟 特徴
- **AI自動翻訳**: OpenAI Whisper (文字起こし) + GPT-4o-mini (翻訳) を使用
- **長尺動画対応**: 4時間を超える動画も自動で分割処理し、API制限を回避
- **字幕生成**: YouTubeや動画プレイヤーで読み込める `.srt` ファイルを出力
- **コスト最適化**: テストモード搭載により、API利用料の無駄遣いを防止

## 🛠️ 必要要件
- Python 3.10 以上
- FFmpeg (音声処理用)
- OpenAI API Key

## 🚀 インストール手順

1. **リポジトリのクローン**
   ```bash
   git clone https://github.com/あなたのユーザー名/リポジトリ名.git
   cd リポジトリ名

```

2. **ライブラリのインストール**
```bash
pip install -r requirements.txt

```


3. **環境変数の設定**
`.env.example` ファイルの名前を `.env` に変更し、ご自身のOpenAI APIキーを設定してください。
```text
OPENAI_API_KEY=sk-proj-xxxxxxxx...

```



## 📖 使い方

### ステップ 1: 文字起こしと翻訳

以下のコマンドを実行し、X.comの動画URLを入力します。

```bash
python transcribe_x.py

```

処理が完了すると、翻訳結果が `transcript.md` に保存されます。

### ステップ 2: 字幕ファイル(.srt)への変換

翻訳結果を動画プレイヤー用フォーマットに変換します。

```bash
python convert_to_srt.py

```

これで `japanese.srt`（字幕ファイル）が生成されます。

### ステップ 3: 動画のダウンロード

映像を確認したい場合は、`yt-dlp` を使って動画ファイル(.mp4)を取得します。

```bash
yt-dlp "動画URL" -o video.mp4

```

---

## 📺 字幕付きで動画を見る方法

生成された `japanese.srt` と `video.mp4` を使って、以下のいずれかの方法で視聴できます。

### 方法 A：VLC Media Playerを使う（推奨）

1. [VLC Media Player](https://www.videolan.org/vlc/index.ja.html) などの対応プレイヤーで `video.mp4` を再生します。
2. 画面上に `japanese.srt` ファイルをドラッグ＆ドロップします。
3. 自動的に字幕が表示されます。

### 方法 B：ファイル名を揃える

多くのプレイヤー（Windows標準の「映画＆テレビ」など）は、動画と字幕のファイル名が同じだと自動で読み込みます。

* `my_movie.mp4`
* `my_movie.srt`
このように名前を揃えて同じフォルダに置き、動画を再生してください。

---

## ⚠️ 注意事項

* 本ツールはOpenAIのAPI（従量課金）を使用します。長時間の動画を処理する際はAPI利用料にご注意ください。
* 生成された `.env` ファイルや著作権のある動画ファイルは、GitHub等にアップロードしないよう `.gitignore` で設定されています。

```

```