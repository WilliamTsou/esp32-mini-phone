"""
假的 ESP32（語音版）— 用來測試 /voice 端點

用法：
    python test_voice.py 你的錄音檔.wav

它會把錄音檔傳給後端，印出「後端聽到什麼」和「AI 回答什麼」。

還沒有錄音檔的話，最簡單的方法：
  手機或電腦的錄音程式隨便錄一句話，存成或轉成 .wav，放進 backend/ 資料夾，
  再執行：  python test_voice.py test.wav
"""

import sys
import json
import urllib.request

URL = "http://127.0.0.1:8000/voice"


def send_voice(wav_path: str) -> dict:
    # 讀出錄音檔的位元組
    with open(wav_path, "rb") as f:
        audio_bytes = f.read()

    # 手動組一個 multipart/form-data 請求（標準庫做法，不用額外套件）
    boundary = "----esp32boundary"
    filename = wav_path.split("/")[-1].split("\\")[-1]
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="audio"; filename="{filename}"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode("utf-8") + audio_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        URL,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python test_voice.py 你的錄音檔.wav")
        sys.exit(1)

    result = send_voice(sys.argv[1])
    print(f"後端聽到：{result['heard']}")
    print(f"AI 回答：{result['answer']}")
