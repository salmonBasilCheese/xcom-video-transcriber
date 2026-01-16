import re

def convert_md_to_srt(input_file="transcript.md", output_file="japanese.srt"):
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    srt_content = ""
    counter = 1
    current_time = ""
    
    # タイムスタンプを探す正規表現 [00:00:00 - 00:00:05]
    time_pattern = re.compile(r"\[(\d{2}:\d{2}:\d{2}) - (\d{2}:\d{2}:\d{2})\]")

    for i, line in enumerate(lines):
        line = line.strip()
        
        # タイムスタンプ行を見つける
        if line.startswith("###"):
            match = time_pattern.search(line)
            if match:
                start = match.group(1).replace(".", ",") + ",000"
                end = match.group(2).replace(".", ",") + ",000"
                current_time = f"{start} --> {end}"

        # 日本語訳の行を見つける
        elif line.startswith("**JP:**"):
            jp_text = line.replace("**JP:**", "").strip()
            
            # SRTフォーマットに追加
            if current_time and jp_text:
                srt_content += f"{counter}\n{current_time}\n{jp_text}\n\n"
                counter += 1
                current_time = "" # リセット

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(srt_content)
    
    print(f"変換完了！ '{output_file}' が作成されました。")

if __name__ == "__main__":
    convert_md_to_srt()