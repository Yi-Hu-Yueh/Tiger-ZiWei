# Tiger-ZiWei standalone Android acceptance

Use only `dist/android/Tiger-ZiWei-standalone-debug.apk` (package `com.tiger.ziwei`, Android 10+).
The Phase 9A server-client APK is superseded. No backend URL is configured in this app.

## Offline deterministic gate

1. Stop the PC Tiger-ZiWei FastAPI process. Do not start a localhost/LAN/remote backend.
2. Disable Wi-Fi and mobile data on Android.
3. Force-stop the app, then launch it. The local UI must open immediately with no server setup.
4. Confirm the API-key field is blank and birth date/time fields are masked by default.
5. Select preset A, then 排盤. Confirm lunar 2025-01-01; pillars 乙巳／丁丑／戊戌／壬子; Life/Body 寅／寅; 土五局; 12 palaces; all stars and transformations.
6. Show/hide birth values; target query values must remain readable. Edit birth data and confirm dependent results invalidate.
7. Confirm all 12 Major-Luck periods and their four transformations.
8. Query Gregorian 2029-02-12, then 2029-02-13. Confirm lunar 2028-12-29 / 2029-01-01 and Flow-Year 2028 / 2029.
9. Query lunar 2026 year only, then month 10, then day 7. Confirm only available Flow-Year/Month/Day layers appear and every layer has all 12 mappings and four transformations.
10. Query Gregorian 2025-07-25 and lunar 2025 leap sixth month day 1. Confirm leap-month normalization and equivalent results.
11. Test presets B, C, L and Z. Case Z 23:59 must retain civil/lunar date; Case L whole leap month uses effective month 7.
12. Inspect the 1648×1648 PNG, zoom it, and save it to Downloads. Verify all 12 cells, center fields, stars, 【命】【身】【祿】【權】【科】【忌】 and Major-Luck ages are readable.
13. With API key still blank, export Word. It must save locally, contain deterministic data and omit unavailable AI sections.
14. Click an AI button with a blank key: 請輸入 NVIDIA API KEY。 With a nonblank key while offline: 無法連線 NVIDIA，請檢查網路。 Deterministic results must remain intact.

Expected: every deterministic operation works with no network and the PC backend stopped.

## User live AI gate (do not automate quota usage)

1. Re-enable Internet while keeping the PC backend stopped.
2. Confirm GLM-5.3-Flash and GPT-OSS-20B are selectable; default is GLM.
3. Enter a user-owned NVIDIA key. Run natal, selected Major-Luck, Flow-Year, Flow-Month and Flow-Day interpretations explicitly.
4. Confirm validated structured outputs, correct scope anchors, correct model metadata, and no provider reasoning content.
5. Change model: all five AI outputs clear, deterministic chart/flow remains, and no automatic AI request occurs.
6. Check GPT-OSS with an explicit interpretation request.
7. Force-stop/restart: the API-key field must be blank again. No key may appear in PNG, Word, logs or storage.

## Word device gate

Generate Case A with the currently valid five AI outputs and full flow query.
Confirm the Downloads success message, open the DOCX in a Word-compatible Android app,
and inspect Chinese text, readable chart image, headings, birth data, natal facts,
12 natal palaces, birth transformations, the complete 12-period Major-Luck table,
all available year/month/day tables and four transformations, and all valid AI sections.
Check filenames at year, month and day granularity, including:
`Tiger_紫微斗數命盤_流年2025-流月閏6-流日1.docx`.

## Build and test

From `android/`: `gradlew.bat testDebugUnitTest assembleDebug --offline`.
Use the resolved JDK and Android SDK paths in JAVA_HOME / ANDROID_HOME.
From the repository root: `.\.venv311\Scripts\python.exe -m pytest -q`.
Normal tests use frozen facts and mocked provider output; live NVIDIA calls are zero.
Never regenerate `golden/` to fix a Kotlin mismatch.

No device means on-device startup, PNG visual, MediaStore save, Word opening and live AI are USER REQUIRED, not PASS.
