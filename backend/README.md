# ESP32 小手機 — 後端

整台小手機的大腦。ESP32 只負責收送，想事情都在這裡。


## 怎麼跑起來

在 `backend/` 資料夾裡：

```bash
python -m venv venv
# 啟動 venv：
#   Windows:  venv\Scripts\activate
#   Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 再把金鑰填進 .env
uvicorn main:app --reload
```

## 怎麼測試

兩種方法，挑一個：

1. **瀏覽器**：打開 http://127.0.0.1:8000/docs ，點 `/ask` → Try it out，輸入問題。
2. **指令**：另開一個終端機，`python test_ask.py`。

看到 AI 的回答，就代表第一步通了。
