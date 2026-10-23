"""
ESP32 小手機 — 後端

端點：
  GET  /        健康檢查
  POST /ask     收文字 → 問 AI → 回文字
  POST /speak   收文字 → 轉語音 → 回聲音（測試發聲用）
  POST /voice   收錄音 → 聽懂 → 問 AI → 轉語音 → 回聲音（完整一條龍）

發聲用 Gemini TTS。它回的是原始聲音資料（PCM），
所以 text_to_speech() 裡會多幾行把它包成 WAV 檔，之後才能播。
想換回別的 TTS，只要改 text_to_speech() 裡面，其他都不用動。

跑起來（在 backend/，先 conda activate esp32）：
    1. pip install -r requirements.txt
    2. uvicorn main:app --reload
打開 http://127.0.0.1:8000/docs 測試。
"""

import io
import os
import time
import tempfile
import wave
import datetime

from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from faster_whisper import WhisperModel
from pydantic import BaseModel

# AI 忙線、重試用完還是失敗時，統一給使用者看／聽到的這句話
BUSY_MESSAGE = "抱歉，AI 現在忙線中，請稍後再試一次。"

# 讀取 .env 裡的金鑰
load_dotenv()

# 建立 Gemini 客戶端
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# 載入 Whisper 語音辨識模型（第一次啟動會自動下載，約 150MB）
whisper = WhisperModel("base", device="cpu", compute_type="int8")

# TTS 的設定：用哪個模型、哪個聲音
TTS_MODEL = "gemini-2.5-flash-preview-tts"
TTS_VOICE = "Kore"   # Gemini 內建的聲音之一，之後可換別的

app = FastAPI(title="ESP32 小手機後端")


# ---- 資料形狀 ----
class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


# ---- AI 問答（含忙線自動重試）----
class AIBusyError(Exception):
    """Gemini 忙線、重試多次仍失敗時丟出，讓上層決定怎麼回應使用者。"""


def ask_ai(question: str, max_retries: int = 3) -> str:
    """
    把一段文字問題交給 Gemini，回傳答案文字。
    遇到「忙線」(503) 會自動等一下再試，最多 max_retries 次。
    每次等待時間加倍（1 秒、2 秒、4 秒），這叫「指數退避」，
    避免大家同時一直重打、把對方壓得更忙。
    """
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=question,
            )
            return response.text
        except genai_errors.ServerError as e:
            # 503 等伺服器端忙線：還有機會就等一下重試
            wait = 2 ** attempt   # 1, 2, 4 秒
            print(f"[ai] 忙線（第 {attempt + 1} 次），{wait} 秒後重試… {e}")
            if attempt < max_retries - 1:
                time.sleep(wait)
            else:
                # 試完都還失敗，往上拋，由端點決定怎麼告訴使用者
                raise AIBusyError() from e


# ---- 文字轉語音（換 TTS 只改這個函式）----
def pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    """Gemini 回的是原始 PCM 聲音資料，這裡幫它加上 WAV 檔頭，變成能播的檔案。"""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)       # 單聲道
        wf.setsampwidth(2)       # 每個取樣 16 bits = 2 bytes
        wf.setframerate(rate)    # Gemini TTS 輸出 24kHz
        wf.writeframes(pcm)
    buffer.seek(0)
    return buffer.read()


def text_to_speech(text: str) -> bytes:
    """把文字變成 WAV 聲音的位元組。用 Gemini TTS。"""
    # 給 TTS 一句明確指令，叫它「只把這段文字唸出來」，
    # 否則它有時會以為要回答問題、改輸出文字，導致 400 錯誤。
    response = client.models.generate_content(
        model=TTS_MODEL,
        contents=f"請用自然的語氣唸出以下這段文字：{text}",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=TTS_VOICE,
                    )
                )
            ),
        ),
    )
    # 取出原始 PCM 聲音資料
    pcm = response.candidates[0].content.parts[0].inline_data.data
    # 包成 WAV 才能播
    return pcm_to_wav(pcm)


# ---- 端點 ----
@app.get("/")
def health_check():
    return {"status": "ok", "message": "後端活著！"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    """收文字 → 問 AI → 回文字。忙線重試用完就回友善訊息。"""
    try:
        return AskResponse(answer=ask_ai(req.question))
    except AIBusyError:
        return AskResponse(answer=BUSY_MESSAGE)


@app.post("/speak")
def speak(req: AskRequest):
    """收文字 → 轉語音 → 回聲音。單獨測發聲用。"""
    audio = text_to_speech(req.question)
    return StreamingResponse(io.BytesIO(audio), media_type="audio/wav")


@app.post("/voice")
async def voice(audio: UploadFile = File(...)):
    """
    完整一條龍：錄音 → 聽懂 → 問 AI → 轉語音 → 回聲音。
    ESP32 只要送一次錄音，就直接拿回可以播的聲音。
    """
    # 1. 把上傳的錄音存成暫存檔，Whisper 要吃檔案
    suffix = os.path.splitext(audio.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        # 2. Whisper 把聲音轉成文字
        segments, _ = whisper.transcribe(tmp_path)
        heard = "".join(seg.text for seg in segments).strip()

        # 3. 問 AI。忙線重試用完，就改用「忙線中」那句話當答案，
        #    使用者會聽到溫柔的說明，而不是整個後端噴 500。
        if not heard:
            answer = "抱歉，我沒有聽清楚。"
        else:
            try:
                answer = ask_ai(heard)
            except AIBusyError:
                answer = BUSY_MESSAGE

        # 4. 把答案轉成聲音
        reply_audio = text_to_speech(answer)
    finally:
        os.remove(tmp_path)

    # 在後端終端機印出來，方便除錯（header 不能放中文，所以改用印的）
    print(f"[voice] 聽到：{heard}")
    print(f"[voice] 回答：{answer}")

    # 5. 回傳聲音
    return StreamingResponse(io.BytesIO(reply_audio), media_type="audio/wav")

@app.post("/voice_save")
async def voice_save(audio: UploadFile = File(...)):
    """跟 /voice 一樣，但把回覆的聲音另存成 last_reply.wav，方便直接雙擊播放。"""
    suffix = os.path.splitext(audio.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        segments, _ = whisper.transcribe(tmp_path)
        heard = "".join(seg.text for seg in segments).strip()
        if not heard:
            answer = "抱歉，我沒有聽清楚。"
        else:
            try:
                answer = ask_ai(heard)
            except AIBusyError:
                answer = BUSY_MESSAGE
        reply_audio = text_to_speech(answer)
    finally:
        os.remove(tmp_path)

    # 存成檔案，方便你直接雙擊聽
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join("audio_out", f"reply_{ts}.wav")
    with open(out_path, "wb") as f:
        f.write(reply_audio)
    print(f"[voice_save] 聽到：{heard}")
    print(f"[voice_save] 回答：{answer}")
    print("[voice_save] 聲音已存成 last_reply.wav，可直接雙擊播放")

    return {"heard": heard, "answer": answer, "saved": "last_reply.wav"}
