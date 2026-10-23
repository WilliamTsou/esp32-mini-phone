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

兩種方法：

1. **瀏覽器**：打開 http://127.0.0.1:8000/docs ，點 `/ask` → Try it out，輸入問題。
2. **指令**：另開一個終端機，`python test_ask.py`。

看到 AI 的回答，就代表第一步通了。

## 怎麼測試
 
兩種方法，挑一個：
 
1. **瀏覽器**：打開 http://127.0.0.1:8000/docs ，點 `/ask` → Try it out，輸入問題。
2. **指令**：另開一個終端機，`python test_ask.py`。
看到 AI 的回答，就代表第一步通了。
 
### 測試 /voice（第二步）
 
先準備一個 `.wav` 錄音檔（手機或電腦隨便錄一句話），放進 `backend/`，然後：
 
```bash
python test_voice.py test.wav
```
 
看到「後端聽到：…」和「AI 回答：…」，就代表語音這條路通了。
也可以用瀏覽器 http://127.0.0.1:8000/docs 的 `/voice` → Try it out 直接上傳檔案。
 
> 第一次跑會自動下載 Whisper 模型（約 150MB），要等一下，之後就不用再下載。
