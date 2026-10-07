# Tiger-ZiWei

Tiger-ZiWei 是一套以 **Python/Kotlin deterministic astrology engine + NVIDIA LLM interpretation** 為核心的紫微斗數系統。設計原則是：**所有曆法、宮位、星曜、四化與運限都由程式確定性計算；LLM 只解讀已計算完成的結構化事實，不參與排盤。**

目前專案同時包含：

- Windows / Browser 版：FastAPI + `/ziwei` Web UI
- Standalone Android 版：Kotlin 本機 deterministic core + packaged local UI + Android Canvas PNG + local DOCX + Android 直接呼叫 NVIDIA HTTPS API

> 最新 Phase 9B 自動驗證已完成 Standalone Core Parity 與 APK Build；**Android 實機安裝、離線執行、AI、PNG 與 Word 視覺驗收仍需使用者本人完成**。

---

## 1. 主要功能

### 本命排盤

- 國曆 / 農曆出生輸入
- 農曆閏月
- 年／月／日／時四柱
- 命宮、身宮
- 十二宮
- 五行局
- 14 主星
- 14 輔星
- 生年四化
- 傳統方盤 PNG
- 本命 AI 解讀

### 大限

- 五行局決定起限歲數
- 陽男陰女順行；陰男陽女逆行
- 第一大限從命宮起
- 12 個大限，每限 10 虛歲
- 大限四化
- 單一指定大限 AI 解讀

### 流年 / 流月 / 流日

- 國曆完整日期 → 自動轉農曆
- 農曆階層式查詢：
  - 只輸入年 → 流年
  - 年＋月 → 流年＋流月
  - 年＋月＋日 → 流年＋流月＋流日
- 流年、流月、流日十二宮
- 流年、流月、流日四化
- 流年、流月、流日 AI 解讀
- 閏月採 Tiger-ZiWei 固定 convention

### 報告與輸出

- PNG 命盤
- 完整 Word DOCX 報告
- Word 可包含目前有效的：
  - 本命資料 / 命盤圖 / 十二宮 / 生年四化 / 本命解讀
  - 12 大限 / 大限四化 / 指定大限解讀
  - 流年 / 流年十二宮 / 流年四化 / 流年解讀
  - 流月 / 流月十二宮 / 流月四化 / 流月解讀
  - 流日 / 流日十二宮 / 流日四化 / 流日解讀
- Word 產生過程 **不重新呼叫 NVIDIA**
- 檔名依有效運限層級附加：`流年YYYY-流月M-流日D`

---

## 2. 核心架構原則

```text
使用者輸入
   │
   ▼
Deterministic Engine
   ├─ Calendar / Lunar / Ganzhi
   ├─ Natal Chart
   ├─ Four Transformations
   ├─ Major-Luck
   ├─ Flow-Year
   ├─ Flow-Month
   └─ Flow-Day
   │
   ├──────────────► PNG / DOCX
   │
   ▼
Structured Facts
   │
   ▼
NVIDIA LLM
   │  （只解讀，不計算）
   ▼
Fact-Lock Validation
   │
   ▼
Validated Interpretation
```

### LLM 不可計算的內容

LLM 不得自行計算或修改：

- 國曆／農曆轉換
- 干支
- 命宮／身宮
- 十二宮
- 五行局
- 主星／輔星位置
- 生年四化
- 大限與大限四化
- 流年／流月／流日與各層四化
- 星曜所在宮位

任何 LLM 回傳若改動 deterministic anchors，後端 / Android fact-lock 應拒絕該結果。

---

## 3. 已鎖定的 Tiger-ZiWei 規則

### 年界

- 主要年界：**農曆正月初一**
- 不採立春作為主要換年界線

### 晚子時

- `23:xx` 視為子時
- **不自動推進民用日期 / 農曆日期**

### 閏月

- Tiger-ZiWei 採用：**整個閏月 N → effective month N+1**
- 與某些「閏月前 15 天／後半月」拆分法不同，屬 `DIFFERENT_CONVENTION`

### 大限

- 第一大限從命宮本宮開始
- 起限歲數＝五行局數：
  - 水二局：2
  - 木三局：3
  - 金四局：4
  - 土五局：5
  - 火六局：6
- 陽男陰女順行
- 陰男陽女逆行
- 每限 10 虛歲

### 壬干四化版本

Tiger-ZiWei 固定採：

| 四化 | 星曜 |
|---|---|
| 化祿 | 天梁 |
| 化權 | 紫微 |
| 化科 | **天府** |
| 化忌 | 武曲 |

與 iztro 的壬化科左輔屬 `EDITION_VARIANT`，Tiger-ZiWei 不跟隨該版本。

---

## 4. AI 模型

目前模型下拉：

| 顯示名稱 | NVIDIA model id | reasoning_effort | clear_thinking |
|---|---|---:|---:|
| GLM-5.3-Flash | `z-ai/glm-5.3-flash` | `low` | `true` |
| GPT-OSS-20B | `openai/gpt-oss-20b` | `low` | 不送出 |

AI 解讀範圍：

1. 本命
2. 大限
3. 流年
4. 流月
5. 流日

### API Key

- Web：使用者輸入 key 時，以 request key 優先；空白時可使用 server `NVIDIA_API_KEY` fallback。
- Standalone Android：**無 server fallback**，使用者必須自行輸入 NVIDIA API key。
- Android API key 不寫入 SharedPreferences、檔案、DB、localStorage、sessionStorage 或 APK。
- App 重啟後 key 應為空白。

---

## 5. Desktop / Browser 架構

```text
Browser /ziwei
   │
   ▼
FastAPI
   ├─ deterministic Python astrology
   ├─ PNG renderer
   ├─ DOCX generator
   └─ NVIDIA client
```

### 啟動

```powershell
cd D:\0TIGER\6months\PythonAPIDevelopment\Tiger-ZiWei
.\.venv311\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 18080
```

瀏覽器：

```text
http://127.0.0.1:18080/ziwei
```

### 主要 API

| Method | Endpoint | 用途 |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/ziwei` | Browser UI |
| GET | `/api/llm/models` | 安全模型清單 |
| POST | `/api/chart` | 本命排盤 |
| POST | `/api/chart/png` | PNG 命盤 |
| POST | `/api/interpret` | 本命解讀 |
| POST | `/api/major-luck/interpret` | 大限解讀 |
| POST | `/api/flow-query` | 國曆／農曆階層式運限查詢 |
| POST | `/api/flow-year/interpret` | 流年解讀 |
| POST | `/api/flow-month/interpret` | 流月解讀 |
| POST | `/api/flow-day/interpret` | 流日解讀 |
| POST | `/api/report/docx` | 完整 Word 報告 |

> `/api/flow-year`、`/api/flow-date` 若仍保留，視為相容 / regression 路徑；產品 UI 應以 `/api/flow-query` 為主。

---

## 6. Standalone Android 架構

Phase 9B 的目標與自動驗證結果是：**Deterministic 功能不需要 PC / FastAPI / LAN Server。**

```text
Android APK
├─ Local packaged UI
├─ ziwei-core (Kotlin)
│  ├─ Calendar adapter
│  ├─ Natal chart
│  ├─ Major-Luck
│  ├─ Flow-Year
│  ├─ Flow-Month
│  └─ Flow-Day
├─ Android Canvas PNG
├─ Local OOXML DOCX
└─ NVIDIA HTTPS client
   └─ 只有 AI 解讀需要網路
```

### Calendar

- Vendored `lunar-java 1.7.7`
- 由 Tiger adapter 覆蓋 / 固定專案 convention
- Python golden fixture 是最終 oracle

### Local UI

- UI asset 打包在 APK
- 使用安全 local HTTPS origin（例如 `appassets.androidplatform.net`）
- 不依賴 `10.0.2.2:18080`
- 不需要 Server URL 設定

### Android AI

```text
Android App
    │ HTTPS
    ▼
https://integrate.api.nvidia.com/v1/chat/completions
```

### Android Word

- 本機 OOXML ZIP generator
- PNG 與所有有效資料直接由手機本機寫入 DOCX
- 使用 MediaStore 存到 Downloads
- 產 Word 時 NVIDIA calls = 0

---

## 7. Android Golden Parity

Phase 9B 使用 Python 目前接受的 deterministic engine 產生 golden fixtures，Android Kotlin 必須完全比對。

最新報告：

- Frozen JSON fixtures：25
- Deterministic parity fixtures：20 / 20 match
- Interpretation fact payload：5 / 5 exact match
- A / B / C / L / Z：PASS
- Major-Luck：PASS
- Flow-Year：PASS
- Flow-Month：PASS
- Flow-Day：PASS
- 四化 10 天干：PASS

Golden manifest：

```text
android/golden/manifest.json
```

Manifest SHA-256（最新 Phase 9B 報告）：

```text
BFDBFDF86C1C8E914B5F69221F7E6318E783D30A49FB9A141C837BE08E654308
```

---

## 8. 測試狀態

最新 Phase 9B 報告：

| 測試 | 結果 |
|---|---:|
| Python regression | 1403 passed / 0 failed / 0 skipped |
| Kotlin core tests | 18 passed |
| Android unit tests | 2 passed |
| Deterministic golden parity | 20 / 20 |
| Interpretation payload parity | 5 / 5 |
| Pytest NVIDIA calls | 0 |
| Phase 9B automated live NVIDIA calls | 0 |

### 仍待人工驗收

- Android APK 實機安裝
- PC backend 關閉後 standalone 啟動
- 飛航模式 deterministic 排盤
- Case L 閏月
- Case Z 晚子時
- Android PNG 視覺
- Android Word 儲存 / 開啟 / 中文 / 表格版面
- Android 直接 NVIDIA AI
- API key 重啟後是否清空

---

## 9. Android APK

最新 Standalone APK 報告路徑：

```text
dist/android/Tiger-ZiWei-standalone-debug.apk
```

最新 Phase 9B 報告：

```text
Size: 3,575,514 bytes
SHA-256: 03E98E15543BE5C7A1E91B059E1F11F272BC2ADE986F439B4D62C59C86531FBF
```

> 上述為目前開發報告中的 build 資訊；最終 release 前仍需 Android 實機驗收。

### 安裝（USB debugging）

```powershell
adb devices
adb install -r "dist\android\Tiger-ZiWei-standalone-debug.apk"
```

---

## 10. 代表性專案結構

```text
Tiger-ZiWei/
├─ app/
│  ├─ api/                 # FastAPI endpoints
│  ├─ calendar/            # Calendar / Ganzhi
│  ├─ llm/                 # NVIDIA clients/interpreters/model registry
│  ├─ models/              # Pydantic domain/result models
│  ├─ report/              # DOCX generator
│  ├─ static/              # Browser UI
│  └─ ziwei/               # Deterministic Python astrology engine
├─ tests/                  # Python regression / fixtures
├─ scripts/
│  └─ export_android_golden.py
├─ android/
│  ├─ app/                 # Android app / local UI / bridge / file output
│  ├─ ziwei-core/          # Pure Kotlin deterministic core
│  └─ golden/              # Frozen Python golden fixtures
├─ output/                 # Local generated reports/images
└─ dist/android/           # Built APKs
```

> 此為架構導向的代表性目錄，實際檔案以 repository 為準。

---

## 11. 安全設計

- API key 不硬編碼
- `.env` 不進 APK
- Android API key 不持久化
- `reasoning_content` 不顯示、不寫入 Word
- LLM deterministic anchors 經 fact-lock
- Word 產生不再次呼叫 AI
- Android local bridge 僅允許明確 allowlisted action
- Android 不提供 shell / arbitrary URL / arbitrary file read bridge
- Standalone release 只需要 HTTPS NVIDIA 網路

---

## 12. 尚未實作

目前刻意不做：

- 流時（Flow-Hour）
- Moving stars / 流曜擴充
- 小限
- 童限

除非有明確產品需求，否則不建議在 release 前繼續擴張 astrology scope。

---

## 13. Release Gate

目前不要因為 APK 已成功 build 就視為正式 release。

Standalone Android 最後必須由使用者本人確認：

1. PC FastAPI 完全關閉。
2. Android App 可開啟。
3. 飛航模式可排盤、大限、流年、流月、流日。
4. PNG 正常。
5. Word 可在手機本機建立、儲存、開啟。
6. 開網路後 NVIDIA 五層解讀可用。
7. App 重啟後 API key 為空。

全部通過後才適合 commit / tag / release。

---

## 14. 技術棧

### Desktop

- Python 3.11.3
- FastAPI
- sxtwl
- Pillow
- python-docx
- NVIDIA NIM / OpenAI-compatible chat completions

### Android

- Kotlin
- Android SDK
- `lunar-java 1.7.7`（vendored / pinned）
- Android WebView local assets / bridge
- Android Canvas / Bitmap
- Local OOXML DOCX generation
- MediaStore Downloads
- NVIDIA HTTPS direct client

---

## 15. 開發原則

1. **Deterministic first**：排盤永遠由程式算。
2. **LLM interpretation only**：LLM 不自行排盤。
3. **Fact Lock**：AI 若更改 deterministic facts，直接拒絕。
4. **Golden parity**：跨平台移植以 Python golden fixtures 為準。
5. **No silent convention changes**：流派差異需明確標示。
6. **No automatic paid AI calls**：只有使用者明確按「解讀」才呼叫 NVIDIA。
7. **Word export = zero NVIDIA**。
8. **Manual runtime gates**：關鍵 UI / Android / Word 必須人工驗收。

---

## 16. Current Status

```text
Desktop deterministic + AI: implemented and regression-tested
Full Word export: implemented
Standalone Android deterministic parity: automated PASS
Standalone Android APK build: PASS
Standalone Android physical-device runtime: PENDING USER VALIDATION
Git final commit/tag: NOT YET PERFORMED
```
