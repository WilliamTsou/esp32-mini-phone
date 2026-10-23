"""
ESP32-mini-phone — backend
 
node:
  GET  /        check the server if it is working
  POST /ask     recieve text request -> ask AI -> send text answer
  POST /voice   recieve voice request → translate into text → ask AI → reply text answer
 
run (backend/):
    1. venv\Scripts\activate          # activate ve
    2. pip install -r requirements.txt
    3. uvicorn main:app --reload
 
run http://127.0.0.1:8000/docs
"""
 
import os
import tempfile
 
from google import genai
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from faster_whisper import WhisperModel
from pydantic import BaseModel

# 讀取 .env 裡的金鑰
load_dotenv()

# 建立一個 AI 客戶端，之後用它來問問題
#client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# 載入 Whisper 語音辨識模型。
# "base" 是最小、最快的版本，在自己電腦上跑很夠用。
# 第一次啟動會自動下載模型檔（約 150MB），要等一下，之後就不用再下載。
whisper = WhisperModel("base", device="cpu", compute_type="int8")

# 建立 FastAPI 應用程式
app = FastAPI(title="ESP32_backend")


# 這是「請求的形狀」：ESP32（或你的測試程式）要傳一個 question 文字過來
class AskRequest(BaseModel):
    question: str


# 這是「回答的形狀」：我們會回一個 answer 文字
class AskResponse(BaseModel):
    answer: str

# ---- /voice 用到的資料形狀 ----
class VoiceResponse(BaseModel):
    heard: str    # Whisper 聽到你說了什麼（方便除錯）
    answer: str   # AI 的回答
 
 
def ask_ai(question: str) -> str:
    """把一段文字問題交給 Gemini，回傳答案文字。
    /ask 和 /voice 都會用到它，所以獨立成一個函式。"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=question,
    )
    return response.text


@app.get("/")
def health_check():
    """To check the server work normally"""
    return {"status": "ok", "message": "working"}


# @app.post("/ask", response_model=AskResponse)
# def ask(req: AskRequest):
    """
    收到一段文字問題，交給 AI，把答案傳回去。
    這就是整台小手機的核心：ESP32 只負責把問題送來、把答案拿回去。
    """
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        messages=[
            {"role": "user", "content": req.question},
        ],
    )

    # AI 的回答包在 message.content 裡，取出文字部分
    answer_text = message.content[0].text
    return AskResponse(answer=answer_text)

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    # 換成 Gemini 的問法
    return AskResponse(answer=ask_ai(req.question))

@app.post("/voice", response_model=VoiceResponse)
async def voice(audio: UploadFile = File(...)):
    """
    收一個錄音檔，整條路跑一遍：
        錄音 → Whisper 轉文字 → 問 AI → 回文字

    之後 ESP32 會把麥克風錄到的聲音傳到這裡；
    現在先用電腦錄一個 .wav 檔來測。
    """
    # 1. 把上傳的錄音先存成一個暫存檔，Whisper 要吃檔案
    suffix = os.path.splitext(audio.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        # 2. Whisper 把聲音轉成文字
        segments, _ = whisper.transcribe(tmp_path)
        heard = "".join(seg.text for seg in segments).strip()

        # 3. 把聽到的文字拿去問 AI
        answer = ask_ai(heard) if heard else "（沒有聽到內容）"
    finally:
        # 4. 收尾：刪掉暫存檔
        os.remove(tmp_path)

    return VoiceResponse(heard=heard, answer=answer)
