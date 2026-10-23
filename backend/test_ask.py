"""
假的 ESP32 — 用來測試 /ask 端點
在後端跑起來以後，另開一個終端機，執行：
    python test_ask.py

它會送一個問題給後端，把 AI 的回答印出來。
這一步沒問題，就代表你的「收文字 → 問 AI → 回文字」整條路通了。
"""

import urllib.request
import json

URL = "http://127.0.0.1:8000/ask"


def ask(question: str) -> str:
    data = json.dumps({"question": question}).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["answer"]


if __name__ == "__main__":
    question = "Answer in one sentence of TCP"
    print(f"Q: {question}")
    print(f"A: {ask(question)}")
