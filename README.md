# ISO 27001 標準簡介｜心智圖動畫

講師：**羅宇倫 Allan Lo**（ISMS／PIMS 輔導顧問・驗證稽核員）

以〈ISO27001:2022（Allan Lo，2023/10/20 更新）〉心智圖為主軸製作的 5 分鐘動畫簡報。畫面沿著心智圖移動、逐層展開，右側卡片補充講師簡報的內容。Allan 老師全程串場講解，助教阿拉蕾在重點處跳出來點綴。

- **本文 0–10 章**：PSDCA 架構，逐章展開 4–10 章條文與要求重點
- **附錄 A**：4 個主題、93 項控制（A.5 組織 37、A.6 人員 8、A.7 實體 14、A.8 技術 34）與其分類
- **控制屬性 → 運作能力**：15 項運作能力，逐一展開對應的控制措施與流程

每個畫面上方都固定顯示課程名稱與講師。

## 檔案

| 檔案 | 說明 |
|---|---|
| `ISO27001_mindmap.mp4` | 完整影片（1600×900，含雙人旁白），可直接播放或插入 PowerPoint |
| `index.html` | 互動版，用瀏覽器開啟後按「開始播放（有聲）」；需與 `assets/` 放在同一層 |
| `docs/分鏡表.md` | 每段的時間、段落與兩位角色的台詞 |
| `narration/lines.json` | 台詞原稿（`A` = Allan 老師，`R` = 阿拉蕾） |
| `assets/` | 角色頭像、旁白音檔 |
| `src/`、`tools/` | 簡報範本、控制措施對照表，以及建置、語音合成與錄影工具 |

## 操作方式（互動版）

- 空白鍵或點擊畫面：播放／暫停
- ← →：上一段／下一段
- F：切換全螢幕
- 點擊進度條：跳到指定時間

## 修改台詞與重新產生

旁白使用 Microsoft Edge 神經語音（台灣國語）：Allan 老師為 `zh-TW-YunJheNeural`，阿拉蕾為 `zh-TW-HsiaoYuNeural`（音調調高、語速加快）。可在 `tools/tts.py` 的 `EDGE` 調整語速與音高。

```bash
pip install edge-tts soundfile imageio-ffmpeg numpy
python tools/tts.py      # 產生 assets/narration.mp3、narration/timing.json（需連線 speech.platform.bing.com）
python tools/build.py    # 重建 index.html，段落長度會跟著旁白調整
```

重新錄製影片（畫面依時間戳記對齊旁白，確保音字同步）：

```bash
node tools/record_video.js   # 需要 Playwright 與 imageio-ffmpeg
```

無法連線時，可改用離線語音 `python tools/tts.py --engine kokoro --model-dir <模型目錄>`（口音偏大陸普通話）。

## 資料來源

- 心智圖：https://www.mindomo.com/zh/mindmap/iso270012022-allan-lo-20231020-f313c58b4e6742c199cf7e89a86e2d7f
- 講師簡報〈ISO 27001標準簡介〉：條文說明、附錄 A 分類，以及控制措施與運作能力（A01–A15）的對應
- Allan 的完整分享：https://sites.google.com/123hi.org/iso27001/
