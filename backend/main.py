"""
ESP32 小手機 — 後端 第一步：/ask 端點
收一段文字 → 問 AI → 回一段文字

跑起來的方法（在 backend/ 資料夾裡）：
    1. python -m venv venv
    2. 啟動 venv：
         Windows:  venv\Scripts\activate
         Mac/Linux: source venv/bin/activate
    3. pip install -r requirements.txt
    4. 把 .env.example 複製成 .env，填入你的金鑰
    5. uvicorn main:app --reload

然後打開瀏覽器到 http://127.0.0.1:8000/docs 就能直接測試。
"""

import os

#from anthropic import Anthropic
from google import genai
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

# 讀取 .env 裡的金鑰
load_dotenv()

# 建立一個 AI 客戶端，之後用它來問問題
#client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# 建立 FastAPI 應用程式
app = FastAPI(title="ESP32_backend")


# 這是「請求的形狀」：ESP32（或你的測試程式）要傳一個 question 文字過來
class AskRequest(BaseModel):
    question: str


# 這是「回答的形狀」：我們會回一個 answer 文字
class AskResponse(BaseModel):
    answer: str


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
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=req.question,
    )
    return AskResponse(answer=response.text)
