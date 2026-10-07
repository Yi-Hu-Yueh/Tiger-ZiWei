"use strict";

// A single UI is shared by desktop HTTP mode and the standalone Android app.
// Android exposes one narrow asynchronous request bridge; no URL or command is
// accepted by native code beyond this fixed mapping.
const isStandaloneAndroid = Boolean(typeof window !== "undefined" && window.TigerAndroid && typeof window.TigerAndroid.request === "function");
if (isStandaloneAndroid) {
  const nativeActions = new Map([
    ["GET /api/llm/models", "get_models"],
    ["POST /api/chart", "calculate_chart"],
    ["POST /api/flow-query", "calculate_flow_query"],
    ["POST /api/chart/png", "generate_png"],
    ["POST /api/interpret", "interpret_natal"],
    ["POST /api/major-luck/interpret", "interpret_major_luck"],
    ["POST /api/flow-year/interpret", "interpret_flow_year"],
    ["POST /api/flow-month/interpret", "interpret_flow_month"],
    ["POST /api/flow-day/interpret", "interpret_flow_day"],
    ["POST /api/report/docx", "generate_docx"]
  ]);
  const pending = new Map();
  const sessionId = Math.random().toString(36).slice(2);
  let sequence = 0;
  const headerObject = (headers) => {
    if (!headers) return {};
    if (headers instanceof Headers) return Object.fromEntries(headers.entries());
    return Object.fromEntries(Object.entries(headers));
  };
  const base64Blob = (encoded, mime) => {
    const binary = atob(encoded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return new Blob([bytes], { type: mime });
  };
  class NativeResponse {
    constructor(success, payload) {
      this.data = payload;
      this.status = success ? 200 : Number(payload.status || 500);
      this.ok = this.status >= 200 && this.status < 300;
      const filename = payload._filename;
      this.headers = { get: (name) => {
        const lower = String(name).toLowerCase();
        if (lower === "content-disposition" && filename) return `attachment; filename*=utf-8''${encodeURIComponent(filename)}`;
        if (lower === "content-type") return payload._mime || "application/json";
        return null;
      } };
    }
    async json() { return this.data; }
    async blob() {
      if (!this.data._binary_base64) throw new Error("本機回應沒有檔案內容。");
      return base64Blob(this.data._binary_base64, this.data._mime || "application/octet-stream");
    }
  }
  window.TigerStandalone = {
    onResponse(requestId, success, raw) {
      const item = pending.get(requestId);
      if (!item) return;
      pending.delete(requestId);
      try { item.resolve(new NativeResponse(Boolean(success), JSON.parse(raw))); }
      catch (_error) { item.reject(new Error("本機回應格式錯誤。")); }
    }
  };
  window.fetch = (url, options = {}) => new Promise((resolve, reject) => {
    const method = String(options.method || "GET").toUpperCase();
    const target = new URL(String(url), location.origin);
    if (target.origin !== location.origin) { reject(new Error("不支援的本機動作。")); return; }
    const path = target.pathname;
    const action = nativeActions.get(`${method} ${path}`);
    if (!action) { reject(new Error("不支援的本機動作。")); return; }
    const requestId = `tiger-${sessionId}-${++sequence}`;
    const abort = () => { pending.delete(requestId); reject(new DOMException("Aborted", "AbortError")); };
    if (options.signal?.aborted) { abort(); return; }
    options.signal?.addEventListener("abort", abort, { once: true });
    pending.set(requestId, { resolve, reject });
    window.TigerAndroid.request(requestId, action, JSON.stringify({
      body: options.body || "",
      headers: headerObject(options.headers),
      saveToDownloads: Boolean(options.saveToDownloads)
    }));
  });
}

const presets = {
  A: { name: "預設 A", gender: "female", birth_year: 2025, birth_month: 1, birth_day: 29, birth_hour: 0, birth_minute: 30, birthplace: "Taipei" },
  B: { name: "預設 B", gender: "female", birth_year: 2025, birth_month: 1, birth_day: 29, birth_hour: 1, birth_minute: 30, birthplace: "Taipei" },
  C: { name: "預設 C", gender: "female", birth_year: 2024, birth_month: 2, birth_day: 29, birth_hour: 12, birth_minute: 0, birthplace: "Taipei" },
  L: { name: "預設 L", gender: "female", birth_year: 2025, birth_month: 7, birth_day: 25, birth_hour: 12, birth_minute: 0, birthplace: "Taipei" },
  Z: { name: "預設 Z", gender: "female", birth_year: 2025, birth_month: 7, birth_day: 24, birth_hour: 23, birth_minute: 59, birthplace: "Taipei" }
};

const form = document.querySelector("#chart-form");
const resultSection = document.querySelector("#result");
const resultTail = document.querySelector("#result-tail");
const errorBox = document.querySelector("#error-message");
const submitButton = document.querySelector("#submit-button");
const birthDateTimeToggle = document.querySelector("#birth-date-time-toggle");
const chartImage = document.querySelector("#chart-image");
const chartImageWrap = document.querySelector("#chart-image-wrap");
const chartDownload = document.querySelector("#chart-download");
const chartFullsize = document.querySelector("#chart-fullsize");
const chartImageLink = document.querySelector("#chart-image-link");
const imageStatus = document.querySelector("#image-status");
const interpretButton = document.querySelector("#interpret-button");
const interpretStatus = document.querySelector("#interpret-status");
const interpretError = document.querySelector("#interpret-error");
const interpretationResult = document.querySelector("#interpretation-result");
const reportButton = document.querySelector("#report-button");
const reportStatus = document.querySelector("#report-status");
const aiModelSelect = document.querySelector("#ai-model-select");
const nvidiaApiKeyInput = document.querySelector("#nvidia-api-key");
if (isStandaloneAndroid) {
  const note = document.querySelector(".ai-settings-note");
  if (note) note.textContent = "金鑰只保留在目前頁面記憶體中；不會儲存，重新啟動後為空白。";
  nvidiaApiKeyInput.value = "";
  const previewNote = document.querySelector(".chart-preview-card .muted");
  if (previewNote) previewNote.textContent = "使用本機排盤結果產生，不需要網路。Word 可匯出現有確定性資料，未解讀的 AI 章節會省略。";
}
const birthDateTimeInputs = [
  "birth_year", "birth_month", "birth_day", "lunar_year", "lunar_month", "lunar_day",
  "birth_hour", "birth_minute"
].map((id) => document.querySelector(`#${id}`));
const flowQueryModeInputs = [...document.querySelectorAll('input[name="flow_query_mode"]')];
const flowSolarInputs = ["target-solar-year", "target-solar-month", "target-solar-day"]
  .map((id) => document.querySelector(`#${id}`));
const flowLunarInputs = ["target-lunar-year", "target-lunar-month", "target-lunar-day"]
  .map((id) => document.querySelector(`#${id}`));
const flowLeapMonthInput = document.querySelector("#target-is-leap-month");
const flowQueryInputs = [...flowSolarInputs, ...flowLunarInputs, flowLeapMonthInput];
const flowYearButton = document.querySelector("#flow-date-button");
const FLOW_DATE_BUTTON_TEXT = "計算流年／流月／流日";
const FLOW_DATE_TIMEOUT_MS = 15_000;
const flowYearStatus = document.querySelector("#flow-year-status");
const flowYearError = document.querySelector("#flow-year-error");
const flowYearResult = document.querySelector("#flow-year-result");
const flowMonthFacts = document.querySelector("#flow-month-facts");
const flowDayFacts = document.querySelector("#flow-day-facts");
const flowYearInterpretButton = document.querySelector("#flow-year-interpret-button");
const flowYearInterpretStatus = document.querySelector("#flow-year-interpret-status");
const flowYearInterpretError = document.querySelector("#flow-year-interpret-error");
const flowYearInterpretationResult = document.querySelector("#flow-year-interpretation-result");
const flowMonthInterpretButton = document.querySelector("#flow-month-interpret-button");
const flowMonthInterpretStatus = document.querySelector("#flow-month-interpret-status");
const flowMonthInterpretError = document.querySelector("#flow-month-interpret-error");
const flowMonthInterpretationResult = document.querySelector("#flow-month-interpretation-result");
const flowDayInterpretButton = document.querySelector("#flow-day-interpret-button");
const flowDayInterpretStatus = document.querySelector("#flow-day-interpret-status");
const flowDayInterpretError = document.querySelector("#flow-day-interpret-error");
const flowDayInterpretationResult = document.querySelector("#flow-day-interpretation-result");
const FLOW_MONTH_INTERPRET_BUTTON_TEXT = "解讀流月";
const FLOW_DAY_INTERPRET_BUTTON_TEXT = "解讀流日";
const STRUCTURED_INTERPRETATION_TIMEOUT_MS = 185_000;
const majorLuckSelect = document.querySelector("#major-luck-select");
const majorLuckInterpretButton = document.querySelector("#major-luck-interpret-button");
const majorLuckInterpretStatus = document.querySelector("#major-luck-interpret-status");
const majorLuckInterpretError = document.querySelector("#major-luck-interpret-error");
const majorLuckInterpretationResult = document.querySelector("#major-luck-interpretation-result");
let chartImageUrl = null;
let birthDateTimeShown = false;
let currentBirthInput = null;
let currentChart = null;
let currentInterpretation = null;
let selectedMajorLuckIndex = null;
let currentMajorLuckInterpretationIndex = null;
let currentMajorLuckInterpretation = null;
let currentFlowYearTarget = null;
let currentFlowYearResult = null;
let currentFlowQueryInput = null;
let currentFlowQueryResult = null;
let currentFlowYearInterpretation = null;
let currentFlowMonthInterpretation = null;
let currentFlowDayInterpretation = null;
let interpretationGeneration = 0;
let flowYearGeneration = 0;
let flowYearInterpretationGeneration = 0;
let flowMonthInterpretationGeneration = 0;
let flowDayInterpretationGeneration = 0;
let majorLuckInterpretationGeneration = 0;
let interpretationInFlight = false;
let reportInFlight = false;
let flowYearInFlight = false;
let flowYearInterpretationInFlight = false;
let flowMonthInterpretationInFlight = false;
let flowDayInterpretationInFlight = false;
let majorLuckInterpretationInFlight = false;
let llmModelDisplayNames = new Map([["z-ai/glm-5.3-flash", "GLM-5.3-Flash"]]);

const palaceOrder = ["命宮", "兄弟宮", "夫妻宮", "子女宮", "財帛宮", "疾厄宮", "遷移宮", "交友宮", "官祿宮", "田宅宮", "福德宮", "父母宮"];
const overallLabels = {
  personality: "性格",
  career: "職涯",
  finance: "財務",
  relationships: "感情",
  interpersonal: "人際",
  family: "家庭",
  strengths: "優勢",
  potential_challenges: "可留意的挑戰"
};
const majorLuckOverallLabels = {
  career: "職涯",
  finance: "財務",
  relationships: "感情",
  family_and_interpersonal: "家庭／人際",
  strengths: "優勢",
  potential_challenges: "可留意的挑戰",
  practical_focus: "實際重點"
};

function setPreset(key) {
  const preset = presets[key];
  if (!preset) return;
  document.querySelector("#calendar-solar").checked = true;
  updateCalendarMode();
  Object.entries(preset).forEach(([field, value]) => {
    const control = document.querySelector(`#${field}`);
    if (control) control.value = value;
  });
  invalidateInterpretation();
  clearError();
}

function selectedCalendarType() {
  return document.querySelector('input[name="calendar_type"]:checked').value;
}

function updateCalendarMode() {
  const lunarMode = selectedCalendarType() === "lunar";
  document.querySelectorAll(".solar-date-field").forEach((field) => {
    field.hidden = lunarMode;
    field.querySelector("input").required = !lunarMode;
  });
  document.querySelectorAll(".lunar-date-field").forEach((field) => {
    field.hidden = !lunarMode;
    const control = field.querySelector("input, select");
    control.required = lunarMode;
  });
}

function setNumericValuesShown(inputs, shown) {
  inputs.forEach((input) => {
    input.type = shown ? "number" : "password";
  });
}

function setBirthDateTimeShown(shown) {
  birthDateTimeShown = shown;
  setNumericValuesShown(birthDateTimeInputs, shown);
  birthDateTimeToggle.setAttribute("aria-pressed", String(shown));
  birthDateTimeToggle.textContent = shown ? "隱藏出生年月日時分" : "顯示出生年月日時分";
}

function collectInput() {
  const value = (id) => document.querySelector(`#${id}`).value;
  const name = value("name").trim();
  const calendarType = selectedCalendarType();
  const common = {
    name: name || null,
    gender: value("gender"),
    calendar_type: calendarType,
    birth_hour: Number(value("birth_hour")),
    birth_minute: Number(value("birth_minute")),
    birthplace: value("birthplace").trim()
  };
  if (calendarType === "lunar") {
    return {
      ...common,
      lunar_year: Number(value("lunar_year")),
      lunar_month: Number(value("lunar_month")),
      lunar_day: Number(value("lunar_day")),
      is_leap_month: value("is_leap_month") === "true"
    };
  }
  return {
    ...common,
    birth_year: Number(value("birth_year")),
    birth_month: Number(value("birth_month")),
    birth_day: Number(value("birth_day"))
  };
}

function selectedFlowQueryMode() {
  return document.querySelector('input[name="flow_query_mode"]:checked').value;
}

function updateFlowQueryMode() {
  const lunarMode = selectedFlowQueryMode() === "lunar";
  document.querySelectorAll(".flow-solar-field").forEach((field) => {
    field.hidden = lunarMode;
    field.querySelector("input").required = !lunarMode;
  });
  document.querySelectorAll(".flow-lunar-field").forEach((field) => {
    field.hidden = !lunarMode;
  });
  document.querySelector("#target-lunar-year").required = lunarMode;
}

function collectFlowQuery() {
  const value = (id) => document.querySelector(`#${id}`).value.trim();
  const mode = selectedFlowQueryMode();
  if (mode === "lunar") {
    return {
      mode,
      year: value("target-lunar-year"),
      month: value("target-lunar-month"),
      day: value("target-lunar-day"),
      is_leap_month: value("target-is-leap-month") === "true"
    };
  }
  return {
    mode,
    year: value("target-solar-year"),
    month: value("target-solar-month"),
    day: value("target-solar-day")
  };
}

function validateFlowQuery(rawQuery) {
  const numeric = (value) => /^\d+$/.test(value);
  if (rawQuery.mode === "solar") {
    const fields = ["year", "month", "day"];
    if (fields.some((field) => rawQuery[field] === "")) {
      return { error: "國曆查詢請完整輸入年、月、日。", value: null };
    }
    if (fields.some((field) => !numeric(rawQuery[field]))) {
      return { error: "請輸入有效的國曆日期。", value: null };
    }
    const query = Object.fromEntries(fields.map((field) => [field, Number(rawQuery[field])]));
    if (query.year < 1583 || query.year > 9999 || query.month < 1 || query.month > 12) {
      return { error: "請輸入有效的國曆日期。", value: null };
    }
    const leapYear = query.year % 4 === 0 && (query.year % 100 !== 0 || query.year % 400 === 0);
    const daysInMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if (query.day < 1 || query.day > daysInMonth[query.month - 1]) {
      return { error: "請輸入有效的國曆日期。", value: null };
    }
    return { error: null, value: { mode: "solar", ...query } };
  }

  if (rawQuery.year === "") {
    return { error: "農曆查詢請輸入年份。", value: null };
  }
  if (!numeric(rawQuery.year) || Number(rawQuery.year) < 1583 || Number(rawQuery.year) > 9999) {
    return { error: "請輸入有效的農曆年份。", value: null };
  }
  if (rawQuery.day !== "" && rawQuery.month === "") {
    return { error: "農曆日必須搭配農曆月。", value: null };
  }
  if (rawQuery.is_leap_month && rawQuery.month === "") {
    return { error: "閏月設定必須搭配農曆月。", value: null };
  }
  if (rawQuery.month !== "" && (!numeric(rawQuery.month) || Number(rawQuery.month) < 1 || Number(rawQuery.month) > 12)) {
    return { error: "農曆月必須介於 1 到 12。", value: null };
  }
  if (rawQuery.day !== "" && (!numeric(rawQuery.day) || Number(rawQuery.day) < 1 || Number(rawQuery.day) > 30)) {
    return { error: "農曆日必須介於 1 到 30。", value: null };
  }
  const query = { mode: "lunar", year: Number(rawQuery.year) };
  if (rawQuery.month !== "") {
    query.month = Number(rawQuery.month);
    query.is_leap_month = rawQuery.is_leap_month;
  }
  if (rawQuery.day !== "") query.day = Number(rawQuery.day);
  return { error: null, value: query };
}

function flowDateUiError(message) {
  const error = new Error(message);
  error.name = "FlowDateUiError";
  return error;
}

async function fetchFlowQuery(request, timeoutMs = FLOW_DATE_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch("/api/flow-query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal: controller.signal
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

async function fetchStructuredFlowInterpretation(url, request, timeoutMs = STRUCTURED_INTERPRETATION_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {
      method: "POST",
      headers: typeof interpretationRequestHeaders === "function"
        ? interpretationRequestHeaders()
        : { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal: controller.signal
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

function interpretationRequestHeaders() {
  const headers = {
    "Content-Type": "application/json",
    "X-Tiger-NVIDIA-Model": aiModelSelect.value || "z-ai/glm-5.3-flash"
  };
  const apiKey = nvidiaApiKeyInput.value.trim();
  if (apiKey) headers["X-Tiger-NVIDIA-API-Key"] = apiKey;
  return headers;
}

function interpretationModelText(payload) {
  const displayName = payload.model_display_name
    || llmModelDisplayNames.get(payload.model)
    || payload.model
    || "未記錄";
  return `AI 模型：${displayName}`;
}

async function loadLlmModels() {
  try {
    const response = await fetch("/api/llm/models", { method: "GET" });
    if (!response.ok) return;
    const models = await response.json();
    if (!Array.isArray(models) || models.length === 0) return;
    const options = models.map((model) => {
      const option = document.createElement("option");
      option.value = model.id;
      option.textContent = model.display_name;
      option.selected = Boolean(model.default);
      return option;
    });
    llmModelDisplayNames = new Map(models.map((model) => [model.id, model.display_name]));
    aiModelSelect.replaceChildren(...options);
  } catch (_error) {
    // Keep the safe static GLM fallback. No secrets are involved in this endpoint.
  }
}

function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
  resultSection.hidden = true;
  resultTail.hidden = true;
}

function clearInterpretation() {
  currentInterpretation = null;
  document.querySelector("#interpret-overview").textContent = "";
  document.querySelector("#interpret-transformations").textContent = "";
  document.querySelector("#palace-interpretations").replaceChildren();
  document.querySelector("#interpret-overall").replaceChildren();
  document.querySelector("#interpret-model").textContent = "";
  interpretationResult.hidden = true;
  interpretStatus.hidden = true;
  interpretStatus.textContent = "";
  interpretError.hidden = true;
  interpretError.textContent = "";
  reportButton.disabled = !isStandaloneAndroid || !currentBirthInput;
  reportStatus.hidden = true;
  reportStatus.textContent = "";
}

function invalidateInterpretation() {
  interpretationGeneration += 1;
  currentBirthInput = null;
  currentChart = null;
  interpretButton.disabled = true;
  clearInterpretation();
  invalidateFlowYear();
  invalidateMajorLuckInterpretation(true);
}

function clearMajorLuckInterpretation() {
  currentMajorLuckInterpretationIndex = null;
  currentMajorLuckInterpretation = null;
  document.querySelector("#major-luck-interpretation-summary").replaceChildren();
  document.querySelector("#major-luck-overview").textContent = "";
  document.querySelector("#major-luck-host-analysis").textContent = "";
  document.querySelector("#major-luck-transformation-analysis").replaceChildren();
  document.querySelector("#major-luck-interpretation-overall").replaceChildren();
  document.querySelector("#major-luck-interpret-model").textContent = "";
  majorLuckInterpretationResult.hidden = true;
  majorLuckInterpretStatus.hidden = true;
  majorLuckInterpretStatus.textContent = "";
  majorLuckInterpretError.hidden = true;
  majorLuckInterpretError.textContent = "";
}

function updateMajorLuckInterpretButton() {
  majorLuckInterpretButton.disabled = majorLuckInterpretationInFlight || !currentBirthInput || majorLuckSelect.value === "";
}

function resetMajorLuckSelector() {
  selectedMajorLuckIndex = null;
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "請先排盤";
  majorLuckSelect.replaceChildren(placeholder);
  majorLuckSelect.disabled = true;
}

function invalidateMajorLuckInterpretation(resetSelector = false) {
  majorLuckInterpretationGeneration += 1;
  clearMajorLuckInterpretation();
  if (resetSelector) resetMajorLuckSelector();
  updateMajorLuckInterpretButton();
}

function clearFlowYear() {
  currentFlowQueryInput = null;
  currentFlowQueryResult = null;
  currentFlowYearResult = null;
  document.querySelector("#flow-date-summary").replaceChildren();
  document.querySelector("#flow-year-summary").replaceChildren();
  document.querySelector("#flow-year-body").replaceChildren();
  document.querySelector("#flow-year-transformation-body").replaceChildren();
  document.querySelector("#flow-month-summary").replaceChildren();
  document.querySelector("#flow-month-body").replaceChildren();
  document.querySelector("#flow-month-transformation-body").replaceChildren();
  document.querySelector("#flow-day-summary").replaceChildren();
  document.querySelector("#flow-day-body").replaceChildren();
  document.querySelector("#flow-day-transformation-body").replaceChildren();
  flowMonthFacts.hidden = true;
  flowDayFacts.hidden = true;
  flowYearResult.hidden = true;
  flowYearStatus.hidden = true;
  flowYearStatus.textContent = "";
  flowYearError.hidden = true;
  flowYearError.textContent = "";
  invalidateFlowYearInterpretation();
  invalidateFlowMonthInterpretation();
  invalidateFlowDayInterpretation();
}

function updateFlowYearButton() {
  flowYearButton.disabled = flowYearInFlight || !currentBirthInput;
}

function invalidateFlowYear() {
  flowYearGeneration += 1;
  clearFlowYear();
  updateFlowYearButton();
}

function clearFlowYearInterpretation() {
  currentFlowYearInterpretation = null;
  document.querySelector("#flow-year-interpretation-summary").replaceChildren();
  document.querySelector("#flow-year-overview").textContent = "";
  document.querySelector("#flow-year-life-analysis").textContent = "";
  document.querySelector("#flow-year-major-luck-context").textContent = "";
  document.querySelector("#flow-year-transformation-analysis").replaceChildren();
  document.querySelector("#flow-year-interpretation-overall").replaceChildren();
  document.querySelector("#flow-year-interpret-model").textContent = "";
  flowYearInterpretationResult.hidden = true;
  flowYearInterpretStatus.hidden = true;
  flowYearInterpretStatus.textContent = "";
  flowYearInterpretError.hidden = true;
  flowYearInterpretError.textContent = "";
}

function updateFlowYearInterpretButton() {
  flowYearInterpretButton.disabled = flowYearInterpretationInFlight || !currentBirthInput || currentFlowYearTarget === null;
}

function invalidateFlowYearInterpretation() {
  flowYearInterpretationGeneration += 1;
  currentFlowYearTarget = null;
  clearFlowYearInterpretation();
  updateFlowYearInterpretButton();
}

function clearFlowMonthInterpretation() {
  currentFlowMonthInterpretation = null;
  document.querySelector("#flow-month-interpretation-summary").replaceChildren();
  document.querySelector("#flow-month-overview").textContent = "";
  document.querySelector("#flow-month-life-analysis").textContent = "";
  document.querySelector("#flow-month-major-luck-context").textContent = "";
  document.querySelector("#flow-month-flow-year-context").textContent = "";
  document.querySelector("#flow-month-transformation-analysis").replaceChildren();
  document.querySelector("#flow-month-interpretation-overall").replaceChildren();
  document.querySelector("#flow-month-interpret-model").textContent = "";
  flowMonthInterpretationResult.hidden = true;
  flowMonthInterpretStatus.hidden = true;
  flowMonthInterpretStatus.textContent = "";
  flowMonthInterpretError.hidden = true;
  flowMonthInterpretError.textContent = "";
}

function updateFlowMonthInterpretButton() {
  flowMonthInterpretButton.disabled = flowMonthInterpretationInFlight || !currentBirthInput || !currentFlowQueryResult?.flow_month;
}

function invalidateFlowMonthInterpretation() {
  flowMonthInterpretationGeneration += 1;
  clearFlowMonthInterpretation();
  updateFlowMonthInterpretButton();
}

function clearFlowDayInterpretation() {
  currentFlowDayInterpretation = null;
  document.querySelector("#flow-day-interpretation-summary").replaceChildren();
  document.querySelector("#flow-day-overview").textContent = "";
  document.querySelector("#flow-day-life-analysis").textContent = "";
  document.querySelector("#flow-day-major-luck-context").textContent = "";
  document.querySelector("#flow-day-flow-year-context").textContent = "";
  document.querySelector("#flow-day-flow-month-context").textContent = "";
  document.querySelector("#flow-day-transformation-analysis").replaceChildren();
  document.querySelector("#flow-day-interpretation-overall").replaceChildren();
  document.querySelector("#flow-day-interpret-model").textContent = "";
  flowDayInterpretationResult.hidden = true;
  flowDayInterpretStatus.hidden = true;
  flowDayInterpretStatus.textContent = "";
  flowDayInterpretError.hidden = true;
  flowDayInterpretError.textContent = "";
}

function updateFlowDayInterpretButton() {
  flowDayInterpretButton.disabled = flowDayInterpretationInFlight || !currentBirthInput || !currentFlowQueryResult?.flow_day;
}

function invalidateFlowDayInterpretation() {
  flowDayInterpretationGeneration += 1;
  clearFlowDayInterpretation();
  updateFlowDayInterpretButton();
}

function invalidateAiInterpretationsForModelChange() {
  interpretationGeneration += 1;
  clearInterpretation();
  interpretButton.disabled = interpretationInFlight || !currentBirthInput;

  majorLuckInterpretationGeneration += 1;
  clearMajorLuckInterpretation();
  updateMajorLuckInterpretButton();

  flowYearInterpretationGeneration += 1;
  clearFlowYearInterpretation();
  updateFlowYearInterpretButton();

  flowMonthInterpretationGeneration += 1;
  clearFlowMonthInterpretation();
  updateFlowMonthInterpretButton();

  flowDayInterpretationGeneration += 1;
  clearFlowDayInterpretation();
  updateFlowDayInterpretButton();
}

function flowYearErrorMessage(status, payload) {
  if (typeof isStandaloneAndroid !== "undefined" && isStandaloneAndroid && typeof payload?.detail === "string") return payload.detail;
  if (status === 422) {
    const code = payload?.detail?.code;
    const message = String(payload?.detail?.message || "").toLowerCase();
    if (code === "INVALID_FLOW_QUERY" && message.includes("earlier than")) {
      return "運限查詢日期不可早於出生日期。";
    }
    return "運限查詢資料無效，請確認年月日與閏月設定。";
  }
  return "運限計算失敗，請稍後再試。";
}

function caughtFlowDateErrorMessage(error) {
  if (error instanceof Error && error.name === "AbortError") return "計算逾時，請重試。";
  if (error instanceof Error && error.name === "FlowDateUiError") return error.message;
  if (error instanceof TypeError) return "網路連線失敗，請重試。";
  return "運限計算失敗，請稍後再試。";
}

function interpretationErrorMessage(status, payload) {
  if (typeof isStandaloneAndroid !== "undefined" && isStandaloneAndroid && typeof payload?.detail === "string") return payload.detail;
  const code = payload?.detail?.code;
  const messages = {
    MISSING_API_KEY: "解盤服務尚未設定 NVIDIA API 金鑰。",
    AUTHENTICATION_ERROR: "NVIDIA 驗證或模型權限失敗。",
    PERMISSION_ERROR: "NVIDIA 驗證或模型權限失敗。",
    PAYMENT_OR_QUOTA_ERROR: "NVIDIA API 額度或計費狀態無法完成解盤。",
    RATE_LIMIT_ERROR: "NVIDIA API 請求過於頻繁，請稍後再試。",
    TIMEOUT: "NVIDIA 解盤逾時，請稍後再試。",
    INVALID_STRUCTURED_RESPONSE: "解盤回應格式驗證失敗。",
    EMPTY_RESPONSE: "模型未回傳可用的解盤內容。",
    TRUNCATED_RESPONSE: "模型回傳的解盤內容不完整。",
    REQUEST_VALIDATION_ERROR: "NVIDIA API 無法接受解盤請求。",
    PROVIDER_ERROR: "NVIDIA 服務暫時無法完成解盤。"
  };
  if (code && messages[code]) return messages[code];
  if (status === 429) return messages.RATE_LIMIT_ERROR;
  if (status === 504) return messages.TIMEOUT;
  return "解盤失敗，請稍後再試。";
}

function caughtFlowInterpretationErrorMessage(error, layer) {
  if (error instanceof Error && error.name === "AbortError") return `${layer}逾時，請重試。`;
  if (error instanceof TypeError) return "網路連線失敗，請重試。";
  return error instanceof Error ? error.message : `${layer}失敗，請稍後再試。`;
}

function chineseError(status, payload) {
  if (typeof isStandaloneAndroid !== "undefined" && isStandaloneAndroid && typeof payload?.detail === "string") return payload.detail;
  if (status === 422) {
    if (payload?.detail?.message) return payload.detail.message;
    const details = Array.isArray(payload?.detail) ? payload.detail : [];
    const fields = details.map((item) => item.loc?.at(-1));
    const messages = details.map((item) => String(item.msg || "").toLowerCase());
    if (fields.includes("birthplace")) return "出生地不可空白。";
    if (fields.includes("gender")) return "性別必須選擇男或女。";
    if (fields.includes("birth_hour")) return "出生時必須介於 0 到 23。";
    if (fields.includes("birth_minute")) return "出生分必須介於 0 到 59。";
    if (messages.some((message) => message.includes("gregorian birth date"))) return "西元出生日期無效，請重新確認年月日。";
    if (fields.some((field) => ["birth_year", "birth_month", "birth_day"].includes(field))) return "西元出生日期無效，請重新確認年月日。";
    return "輸入資料無效，請檢查所有欄位。";
  }
  return "排盤失敗，請稍後再試。";
}

function ganzhiText(value) {
  if (!value) return "—";
  return value.display || `${value.heavenly_stem || ""}${value.earthly_branch || ""}` || "—";
}

function lunarMonthText(month) {
  const names = ["", "正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "臘"];
  return names[month] || String(month);
}

function lunarDayText(day) {
  const names = ["", "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十", "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十", "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"];
  return names[day] || String(day);
}

function appendTextCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = value || "—";
  if (!value) cell.classList.add("empty");
  row.appendChild(cell);
  return cell;
}

function addSummary(label, value) {
  const item = document.createElement("div");
  item.className = "summary-item";
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value || "—";
  item.append(term, description);
  document.querySelector("#summary").appendChild(item);
}

function addMajorLuckSummary(label, value) {
  const item = document.createElement("div");
  item.className = "summary-item";
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value || "—";
  item.append(term, description);
  document.querySelector("#major-luck-summary").appendChild(item);
}

function addDynamicSummary(containerId, label, value) {
  const item = document.createElement("div");
  item.className = "summary-item";
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value || "—";
  item.append(term, description);
  document.querySelector(`#${containerId}`).appendChild(item);
}

function addFlowYearSummary(label, value) {
  addDynamicSummary("flow-year-summary", label, value);
}

function addMajorLuckInterpretationSummary(label, value) {
  const item = document.createElement("div");
  item.className = "summary-item";
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value || "—";
  item.append(term, description);
  document.querySelector("#major-luck-interpretation-summary").appendChild(item);
}

function renderSummary(chart, input) {
  const container = document.querySelector("#summary");
  container.replaceChildren();
  const birth = chart.birth_data;
  const calendar = chart.calendar;
  const lunar = calendar.lunar_date;
  const layout = chart.palace_layout;
  const lifePalace = chart.palaces.find((palace) => palace.is_life_palace);
  const bodyPalace = chart.palaces.find((palace) => palace.has_body_palace);
  const lunarText = `${lunar.year} 年${lunar.is_leap_month ? "閏" : ""}${lunarMonthText(lunar.month)}月${lunarDayText(lunar.day)}`;
  const inputWasLunar = input.calendar_type === "lunar";
  const originalInputText = inputWasLunar
    ? `${input.lunar_year} 年${input.is_leap_month ? "閏" : ""}${lunarMonthText(input.lunar_month)}月${lunarDayText(input.lunar_day)}`
    : calendar.solar_date;

  addSummary("姓名", birth.name || "未填寫");
  addSummary("輸入方式", inputWasLunar ? "農曆" : "國曆");
  addSummary("輸入", originalInputText);
  addSummary(inputWasLunar ? "換算國曆" : "換算農曆", inputWasLunar ? calendar.solar_date : lunarText);
  addSummary("西元日期", calendar.solar_date);
  addSummary("出生時間", `${String(birth.birth_hour).padStart(2, "0")}:${String(birth.birth_minute).padStart(2, "0")}`);
  addSummary("出生地", birth.birthplace);
  addSummary("農曆日期", lunarText);
  addSummary("年柱", ganzhiText(calendar.year_ganzhi));
  addSummary("月柱", ganzhiText(calendar.month_ganzhi));
  addSummary("日柱", ganzhiText(calendar.day_ganzhi));
  addSummary("時柱", ganzhiText(calendar.hour_ganzhi));
  addSummary("命宮", lifePalace ? lifePalace.earthly_branch : layout.life_palace_branch);
  addSummary("身宮", bodyPalace ? bodyPalace.earthly_branch : layout.body_palace_branch);
  addSummary("身宮宿宮", chart.body_palace_name || (bodyPalace && bodyPalace.palace_name));
  addSummary("五行局", chart.five_elements_bureau.bureau_name || `${chart.five_elements_bureau.bureau_number}局`);
  addSummary("閏月實際月份", `${lunar.month} 月`);
  addSummary("是否閏月", lunar.is_leap_month ? "是" : "否");
  addSummary("有效月份", `${layout.effective_lunar_month} 月`);
}

function renderPalaces(chart) {
  const body = document.querySelector("#palace-body");
  body.replaceChildren();
  const transformations = chart.birth_year_transformations.transformations;

  chart.palaces.forEach((palace) => {
    const row = document.createElement("tr");
    appendTextCell(row, palace.earthly_branch);
    appendTextCell(row, palace.palace_name);
    appendTextCell(row, ganzhiText(palace.palace_ganzhi));

    appendTextCell(row, palace.is_life_palace ? "命" : "");
    appendTextCell(row, palace.has_body_palace ? "身" : "");

    appendTextCell(row, palace.major_stars.map((star) => star.name).join("、"));
    appendTextCell(row, palace.auxiliary_stars.map((star) => star.name).join("、"));
    const palaceChanges = transformations
      .filter((item) => item.earthly_branch === palace.earthly_branch)
      .map((item) => `${item.transformation}・${item.star_name}`)
      .join("、");
    appendTextCell(row, palaceChanges);
    body.appendChild(row);
  });
}

function renderTransformations(chart) {
  const body = document.querySelector("#transformation-body");
  body.replaceChildren();
  chart.birth_year_transformations.transformations.forEach((item) => {
    const row = document.createElement("tr");
    appendTextCell(row, item.transformation);
    appendTextCell(row, item.star_name);
    appendTextCell(row, item.star_category === "major" ? "主星" : "輔星");
    appendTextCell(row, item.earthly_branch);
    appendTextCell(row, item.palace_name);
    body.appendChild(row);
  });
}

function renderMajorLuck(chart) {
  const summary = document.querySelector("#major-luck-summary");
  const body = document.querySelector("#major-luck-body");
  summary.replaceChildren();
  body.replaceChildren();
  const result = chart.major_luck;
  const genderText = result.gender === "female" ? "女性" : "男性";
  const genderMarker = result.gender === "female" ? "女" : "男";
  const first = result.periods[0];

  addMajorLuckSummary("年干", `${result.year_heavenly_stem}年`);
  addMajorLuckSummary("性別", genderText);
  addMajorLuckSummary("陰陽性別", `${result.year_yinyang}${genderMarker}`);
  addMajorLuckSummary("大限方向", result.direction);
  addMajorLuckSummary("五行局", result.bureau_name);
  addMajorLuckSummary("起限", `${first.start_nominal_age}歲起限`);

  result.periods.forEach((period) => {
    const periodTransformations = result.period_transformations.find(
      (item) => item.major_luck_index === period.index
    );
    const row = document.createElement("tr");
    appendTextCell(row, String(period.index));
    appendTextCell(row, `${period.start_nominal_age}–${period.end_nominal_age}`);
    appendTextCell(row, period.earthly_branch);
    appendTextCell(row, period.palace_name);
    appendTextCell(row, ganzhiText(period.palace_ganzhi));
    const transformationText = periodTransformations
      ? periodTransformations.transformations
        .map((item) => `${item.transformation_type.replace("化", "")} ${item.star_name}`)
        .join("、")
      : "";
    appendTextCell(row, transformationText);
    body.appendChild(row);
  });

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "請選擇大限";
  const options = result.periods.map((period) => {
    const option = document.createElement("option");
    option.value = String(period.index);
    option.textContent = `${period.start_nominal_age}–${period.end_nominal_age}｜${period.palace_name}｜${ganzhiText(period.palace_ganzhi)}`;
    return option;
  });
  majorLuckSelect.replaceChildren(placeholder, ...options);
  majorLuckSelect.disabled = false;
  updateMajorLuckInterpretButton();
}

function renderMajorLuckInterpretation(payload) {
  document.querySelector("#major-luck-interpret-model").textContent = interpretationModelText(payload);
  addMajorLuckInterpretationSummary("大限", `${payload.start_nominal_age}–${payload.end_nominal_age}`);
  addMajorLuckInterpretationSummary("宮位", payload.palace_name);
  addMajorLuckInterpretationSummary("干支", ganzhiText(payload.palace_ganzhi));
  document.querySelector("#major-luck-overview").textContent = payload.overview;
  document.querySelector("#major-luck-host-analysis").textContent = payload.host_palace_analysis;

  const transformations = document.querySelector("#major-luck-transformation-analysis");
  payload.transformation_analysis.forEach((item) => {
    const article = document.createElement("article");
    article.className = "interpretation-item";
    const heading = document.createElement("h4");
    const analysis = document.createElement("p");
    heading.textContent = `${item.transformation_type}｜${item.star_name}｜${item.natal_palace_name}`;
    analysis.textContent = item.analysis;
    article.append(heading, analysis);
    transformations.appendChild(article);
  });

  const overall = document.querySelector("#major-luck-interpretation-overall");
  Object.entries(majorLuckOverallLabels).forEach(([field, label]) => {
    const item = document.createElement("div");
    item.className = "overall-item";
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = payload[field];
    item.append(term, description);
    overall.appendChild(item);
  });
  majorLuckInterpretationResult.hidden = false;
}

function renderFlowYear(payload) {
  const lifePalace = payload.palaces.find((palace) => palace.flow_palace_name === "命宮");
  const active = payload.active_major_luck;
  let majorLuckText = "—";
  if (active) {
    majorLuckText = `${active.start_nominal_age}–${active.end_nominal_age}歲｜${ganzhiText(active.palace_ganzhi)}｜${active.palace_name}`;
  } else if (payload.before_first_major_luck) {
    majorLuckText = "尚未進入第一大限";
  } else if (payload.after_supported_major_luck) {
    majorLuckText = "超出目前支援的大限範圍";
  }

  addFlowYearSummary("流年年份", String(payload.target_lunar_year));
  addFlowYearSummary("流年干支", ganzhiText(payload.ganzhi));
  addFlowYearSummary("虛歲", `${payload.nominal_age} 歲`);
  addFlowYearSummary("流年命宮", payload.flow_life_palace_branch);
  addFlowYearSummary("所在本命宮", lifePalace ? `${lifePalace.natal_palace_name}｜${ganzhiText(lifePalace.natal_palace_ganzhi)}` : "—");
  addFlowYearSummary("目前大限", majorLuckText);

  const transformationBody = document.querySelector("#flow-year-transformation-body");
  payload.transformations.forEach((item) => {
    const row = document.createElement("tr");
    appendTextCell(row, item.transformation_type.replace("化", ""));
    appendTextCell(row, item.star_name);
    appendTextCell(row, item.star_category === "major" ? "主星" : "輔星");
    appendTextCell(row, item.natal_palace_name);
    appendTextCell(row, item.earthly_branch);
    transformationBody.appendChild(row);
  });

  const body = document.querySelector("#flow-year-body");
  payload.palaces.forEach((palace) => {
    const row = document.createElement("tr");
    appendTextCell(row, palace.flow_palace_name);
    appendTextCell(row, palace.earthly_branch);
    appendTextCell(row, palace.natal_palace_name);
    appendTextCell(row, ganzhiText(palace.natal_palace_ganzhi));
    body.appendChild(row);
  });
  flowYearResult.hidden = false;
  currentFlowYearResult = payload;
  currentFlowYearTarget = payload.target_lunar_year;
  updateFlowYearInterpretButton();
}

function renderFlowQuery(payload, queryInput) {
  const target = payload.normalized_target;
  const lunarMonth = target.lunar_month === null
    ? ""
    : `${target.is_leap_month ? "閏" : ""}${lunarMonthText(target.lunar_month)}月`;
  const lunarDate = `${target.lunar_year} 年${lunarMonth}${target.lunar_day === null ? "" : lunarDayText(target.lunar_day)}`;
  addDynamicSummary("flow-date-summary", "查詢類型", payload.query_mode === "solar" ? "國曆" : "農曆");
  if (payload.query_mode === "solar") {
    addDynamicSummary("flow-date-summary", "輸入國曆", target.original_solar_date);
    addDynamicSummary("flow-date-summary", "轉換農曆", lunarDate);
  } else {
    addDynamicSummary("flow-date-summary", "輸入農曆", lunarDate);
    if (target.converted_solar_date) addDynamicSummary("flow-date-summary", "換算國曆", target.converted_solar_date);
  }

  renderFlowYear(payload.flow_year);

  if (payload.flow_month) {
    const month = payload.flow_month;
    addDynamicSummary("flow-month-summary", "農曆年", String(month.lunar_year));
    addDynamicSummary("flow-month-summary", "農曆月", `${month.is_leap_month ? "閏" : ""}${month.lunar_month} 月`);
    addDynamicSummary("flow-month-summary", "有效月份", `${month.effective_month} 月`);
    addDynamicSummary("flow-month-summary", "流月干支", ganzhiText(month.month_ganzhi));
    addDynamicSummary("flow-month-summary", "流月命宮", month.flow_month_life_palace_branch);
    addDynamicSummary("flow-month-summary", "所落本命宮", `${month.natal_host_palace_name}｜${ganzhiText(month.natal_host_palace_ganzhi)}`);
    const monthBody = document.querySelector("#flow-month-body");
    month.palaces.forEach((palace) => {
      const row = document.createElement("tr");
      appendTextCell(row, palace.flow_palace_name);
      appendTextCell(row, palace.earthly_branch);
      appendTextCell(row, palace.natal_palace_name);
      appendTextCell(row, ganzhiText(palace.natal_palace_ganzhi));
      monthBody.appendChild(row);
    });
    const monthTransformations = document.querySelector("#flow-month-transformation-body");
    month.transformations.forEach((item) => {
      const row = document.createElement("tr");
      appendTextCell(row, item.transformation_type.replace("化", ""));
      appendTextCell(row, item.star_name);
      appendTextCell(row, item.star_category === "major" ? "主星" : "輔星");
      appendTextCell(row, item.natal_palace_name);
      appendTextCell(row, item.natal_branch);
      monthTransformations.appendChild(row);
    });
    flowMonthFacts.hidden = false;
  }

  if (payload.flow_day) {
    const day = payload.flow_day;
    addDynamicSummary("flow-day-summary", "目標農曆日期", lunarDate);
    addDynamicSummary("flow-day-summary", "流日干支", ganzhiText(day.day_ganzhi));
    addDynamicSummary("flow-day-summary", "流日命宮", day.flow_day_life_palace_branch);
    addDynamicSummary("flow-day-summary", "所落本命宮", `${day.natal_host_palace_name}｜${ganzhiText(day.natal_host_palace_ganzhi)}`);
    const dayBody = document.querySelector("#flow-day-body");
    day.palaces.forEach((palace) => {
      const row = document.createElement("tr");
      appendTextCell(row, palace.flow_palace_name);
      appendTextCell(row, palace.earthly_branch);
      appendTextCell(row, palace.natal_palace_name);
      appendTextCell(row, ganzhiText(palace.natal_palace_ganzhi));
      dayBody.appendChild(row);
    });
    const dayTransformations = document.querySelector("#flow-day-transformation-body");
    day.transformations.forEach((item) => {
      const row = document.createElement("tr");
      appendTextCell(row, item.transformation_type.replace("化", ""));
      appendTextCell(row, item.star_name);
      appendTextCell(row, item.star_category === "major" ? "主星" : "輔星");
      appendTextCell(row, item.natal_palace_name);
      appendTextCell(row, item.natal_branch);
      dayTransformations.appendChild(row);
    });
    flowDayFacts.hidden = false;
  }

  currentFlowQueryInput = { ...queryInput };
  currentFlowQueryResult = payload;
  flowYearResult.hidden = false;
  updateFlowMonthInterpretButton();
  updateFlowDayInterpretButton();
}

function addFlowYearInterpretationSummary(label, value) {
  const item = document.createElement("div");
  item.className = "summary-item";
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value;
  item.append(term, description);
  document.querySelector("#flow-year-interpretation-summary").appendChild(item);
}

function renderFlowYearInterpretation(payload) {
  document.querySelector("#flow-year-interpret-model").textContent = interpretationModelText(payload);
  const host = payload.flow_life_palace_natal_host;
  const active = payload.active_major_luck_summary;
  let majorLuckText = "尚未進入第一大限";
  if (active.status === "active") {
    majorLuckText = `${active.start_nominal_age}–${active.end_nominal_age}歲｜${ganzhiText(active.palace_ganzhi)}｜${active.palace_name}`;
  } else if (active.status === "after_supported_major_luck") {
    majorLuckText = "超出目前支援的大限範圍";
  }
  addFlowYearInterpretationSummary("流年年份", String(payload.target_year));
  addFlowYearInterpretationSummary("流年干支", ganzhiText(payload.flow_year_ganzhi));
  addFlowYearInterpretationSummary("虛歲", `${payload.nominal_age} 歲`);
  addFlowYearInterpretationSummary("流年命宮", payload.flow_life_palace_branch);
  addFlowYearInterpretationSummary("所在本命宮", `${host.palace_name}｜${ganzhiText(host.palace_ganzhi)}`);
  addFlowYearInterpretationSummary("目前大限", majorLuckText);
  document.querySelector("#flow-year-overview").textContent = payload.overview;
  document.querySelector("#flow-year-life-analysis").textContent = payload.flow_life_palace_analysis;
  document.querySelector("#flow-year-major-luck-context").textContent = payload.major_luck_context;

  const transformations = document.querySelector("#flow-year-transformation-analysis");
  payload.transformation_analysis.forEach((item) => {
    const article = document.createElement("article");
    article.className = "interpretation-item";
    const heading = document.createElement("h4");
    const analysis = document.createElement("p");
    heading.textContent = `${item.transformation_type}｜${item.star_name}｜本命${item.natal_palace_name}`;
    analysis.textContent = item.analysis;
    article.append(heading, analysis);
    transformations.appendChild(article);
  });

  const overall = document.querySelector("#flow-year-interpretation-overall");
  Object.entries(majorLuckOverallLabels).forEach(([field, label]) => {
    const item = document.createElement("div");
    item.className = "overall-item";
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = payload[field];
    item.append(term, description);
    overall.appendChild(item);
  });
  flowYearInterpretationResult.hidden = false;
  currentFlowYearInterpretation = payload;
}

function addFlowPeriodInterpretationSummary(containerId, label, value) {
  const item = document.createElement("div");
  item.className = "summary-item";
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value;
  item.append(term, description);
  document.querySelector(`#${containerId}`).appendChild(item);
}

function renderFlowPeriodTransformations(containerId, payload) {
  const container = document.querySelector(`#${containerId}`);
  payload.transformation_analysis.forEach((item) => {
    const article = document.createElement("article");
    article.className = "interpretation-item";
    const heading = document.createElement("h4");
    const analysis = document.createElement("p");
    heading.textContent = `${item.transformation_type}｜${item.star_name}｜本命${item.natal_palace_name}`;
    analysis.textContent = item.analysis;
    article.append(heading, analysis);
    container.appendChild(article);
  });
}

function renderFlowPeriodOverall(containerId, payload, labels) {
  const container = document.querySelector(`#${containerId}`);
  Object.entries(labels).forEach(([field, label]) => {
    const item = document.createElement("div");
    item.className = "overall-item";
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = payload[field];
    item.append(term, description);
    container.appendChild(item);
  });
}

function renderFlowMonthInterpretation(payload) {
  document.querySelector("#flow-month-interpret-model").textContent = interpretationModelText(payload);
  addFlowPeriodInterpretationSummary("flow-month-interpretation-summary", "農曆年月", `${payload.lunar_year} 年${payload.is_leap_month ? "閏" : ""}${payload.lunar_month} 月`);
  addFlowPeriodInterpretationSummary("flow-month-interpretation-summary", "流月干支", ganzhiText(payload.month_ganzhi));
  addFlowPeriodInterpretationSummary("flow-month-interpretation-summary", "流月命宮", payload.flow_month_life_palace_branch);
  addFlowPeriodInterpretationSummary("flow-month-interpretation-summary", "所落本命宮", payload.natal_host_palace);
  document.querySelector("#flow-month-overview").textContent = payload.overview;
  document.querySelector("#flow-month-life-analysis").textContent = payload.life_palace_analysis;
  document.querySelector("#flow-month-major-luck-context").textContent = payload.major_luck_context;
  document.querySelector("#flow-month-flow-year-context").textContent = payload.flow_year_context;
  renderFlowPeriodTransformations("flow-month-transformation-analysis", payload);
  renderFlowPeriodOverall("flow-month-interpretation-overall", payload, {
    career: "職涯", finance: "財務", relationships: "感情",
    family_and_interpersonal: "家庭／人際", strengths: "優勢",
    potential_challenges: "挑戰", practical_focus: "實際重點"
  });
  flowMonthInterpretationResult.hidden = false;
  currentFlowMonthInterpretation = payload;
}

function renderFlowDayInterpretation(payload) {
  document.querySelector("#flow-day-interpret-model").textContent = interpretationModelText(payload);
  addFlowPeriodInterpretationSummary("flow-day-interpretation-summary", "農曆日期", `${payload.lunar_year} 年${payload.is_leap_month ? "閏" : ""}${payload.lunar_month} 月${payload.lunar_day} 日`);
  addFlowPeriodInterpretationSummary("flow-day-interpretation-summary", "流日干支", ganzhiText(payload.day_ganzhi));
  addFlowPeriodInterpretationSummary("flow-day-interpretation-summary", "流日命宮", payload.flow_day_life_palace_branch);
  addFlowPeriodInterpretationSummary("flow-day-interpretation-summary", "所落本命宮", payload.natal_host_palace);
  document.querySelector("#flow-day-overview").textContent = payload.overview;
  document.querySelector("#flow-day-life-analysis").textContent = payload.life_palace_analysis;
  document.querySelector("#flow-day-major-luck-context").textContent = payload.major_luck_context;
  document.querySelector("#flow-day-flow-year-context").textContent = payload.flow_year_context;
  document.querySelector("#flow-day-flow-month-context").textContent = payload.flow_month_context;
  renderFlowPeriodTransformations("flow-day-transformation-analysis", payload);
  renderFlowPeriodOverall("flow-day-interpretation-overall", payload, {
    work: "工作", finance: "財務", relationships: "感情",
    family_and_interpersonal: "家庭／人際", strengths: "優勢",
    potential_challenges: "挑戰", practical_focus: "實際重點"
  });
  flowDayInterpretationResult.hidden = false;
  currentFlowDayInterpretation = payload;
}

function renderInterpretation(payload) {
  document.querySelector("#interpret-model").textContent = interpretationModelText(payload);
  document.querySelector("#interpret-overview").textContent = payload.overview;
  document.querySelector("#interpret-transformations").textContent = payload.transformation_analysis;

  const byPalace = new Map(payload.palace_interpretations.map((item) => [item.palace_name, item.summary]));
  const palaceContainer = document.querySelector("#palace-interpretations");
  palaceContainer.replaceChildren();
  palaceOrder.forEach((palaceName) => {
    const article = document.createElement("article");
    article.className = "interpretation-item";
    const heading = document.createElement("h4");
    const summary = document.createElement("p");
    heading.textContent = palaceName;
    summary.textContent = byPalace.get(palaceName) || "—";
    article.append(heading, summary);
    palaceContainer.appendChild(article);
  });

  const overall = document.querySelector("#interpret-overall");
  overall.replaceChildren();
  Object.entries(overallLabels).forEach(([field, label]) => {
    const item = document.createElement("div");
    item.className = "overall-item";
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = payload.overall[field];
    item.append(term, description);
    overall.appendChild(item);
  });

  interpretationResult.hidden = false;
}

function renderChart(chart, input) {
  renderSummary(chart, input);
  renderMajorLuck(chart);
  renderPalaces(chart);
  renderTransformations(chart);
  resultSection.hidden = false;
  resultTail.hidden = false;
  resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function responseFilename(response, fallback = "Tiger-ZiWei_紫微命盤.png") {
  const disposition = response.headers.get("Content-Disposition") || "";
  const encoded = disposition.match(/filename\*=utf-8''([^;]+)/i);
  if (encoded) return decodeURIComponent(encoded[1]);
  const plain = disposition.match(/filename="?([^";]+)"?/i);
  return plain ? plain[1] : fallback;
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Word 報告讀取失敗。"));
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] || "");
    reader.readAsDataURL(blob);
  });
}

async function renderChartImage(input) {
  imageStatus.hidden = false;
  imageStatus.textContent = "正在產生命盤圖…";
  chartImageWrap.hidden = true;
  chartDownload.hidden = true;
  chartFullsize.hidden = true;
  const response = await fetch("/api/chart/png", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
  const filename = responseFilename(response);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(chineseError(response.status, payload));
  }
  const blob = await response.blob();
  if (chartImageUrl) URL.revokeObjectURL(chartImageUrl);
  chartImageUrl = URL.createObjectURL(blob);
  chartImage.src = chartImageUrl;
  chartImageLink.href = chartImageUrl;
  chartFullsize.href = chartImageUrl;
  chartDownload.href = chartImageUrl;
  chartDownload.download = filename;
  chartImageWrap.hidden = false;
  chartDownload.hidden = false;
  chartFullsize.hidden = false;
  imageStatus.hidden = true;
}

if (isStandaloneAndroid) {
  chartDownload.addEventListener("click", async (event) => {
    event.preventDefault();
    if (!currentBirthInput) return;
    try {
      const response = await fetch("/api/chart/png", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(currentBirthInput), saveToDownloads: true
      });
      const payload = await response.json();
      if (!response.ok || !payload.saved) throw new Error("PNG 命盤儲存失敗。");
      imageStatus.hidden = false;
      imageStatus.textContent = payload.message;
    } catch (error) {
      imageStatus.hidden = false;
      imageStatus.textContent = error instanceof Error ? error.message : "PNG 命盤儲存失敗。";
    }
  });
  const expandLocalImage = (event) => {
    event.preventDefault();
    chartImageWrap.classList.toggle("standalone-fullsize");
  };
  chartFullsize.addEventListener("click", expandLocalImage);
  chartImageLink.addEventListener("click", expandLocalImage);
}

document.querySelectorAll(".preset").forEach((button) => {
  button.addEventListener("click", () => setPreset(button.dataset.preset));
});

document.querySelectorAll('input[name="calendar_type"]').forEach((control) => {
  control.addEventListener("change", updateCalendarMode);
});

birthDateTimeToggle.addEventListener("click", () => {
  setBirthDateTimeShown(!birthDateTimeShown);
});

form.addEventListener("input", () => {
  invalidateInterpretation();
});

aiModelSelect.addEventListener("change", invalidateAiInterpretationsForModelChange);
aiModelSelect.addEventListener("focus", loadLlmModels, { once: true });

flowQueryInputs.forEach((input) => {
  input.addEventListener(input === flowLeapMonthInput ? "change" : "input", () => {
    invalidateFlowYear();
  });
});

flowQueryModeInputs.forEach((input) => {
  input.addEventListener("change", () => {
    updateFlowQueryMode();
    invalidateFlowYear();
  });
});

majorLuckSelect.addEventListener("change", () => {
  selectedMajorLuckIndex = majorLuckSelect.value === "" ? null : Number(majorLuckSelect.value);
  invalidateMajorLuckInterpretation();
});

majorLuckInterpretButton.addEventListener("click", async () => {
  if (!currentBirthInput || majorLuckInterpretationInFlight || selectedMajorLuckIndex === null) return;
  const requestGeneration = majorLuckInterpretationGeneration;
  const request = {
    birth_input: { ...currentBirthInput },
    major_luck_index: selectedMajorLuckIndex
  };
  majorLuckInterpretationInFlight = true;
  clearMajorLuckInterpretation();
  updateMajorLuckInterpretButton();
  majorLuckInterpretStatus.textContent = "正在解讀大限……";
  majorLuckInterpretStatus.hidden = false;
  try {
    const response = await fetch("/api/major-luck/interpret", {
      method: "POST",
      headers: interpretationRequestHeaders(),
      body: JSON.stringify(request)
    });
    const payload = await response.json().catch(() => ({}));
    if (requestGeneration !== majorLuckInterpretationGeneration) return;
    if (!response.ok) throw new Error(interpretationErrorMessage(response.status, payload));
    renderMajorLuckInterpretation(payload);
    currentMajorLuckInterpretationIndex = request.major_luck_index;
    currentMajorLuckInterpretation = payload;
    majorLuckInterpretStatus.hidden = true;
    majorLuckInterpretStatus.textContent = "";
  } catch (error) {
    if (requestGeneration !== majorLuckInterpretationGeneration) return;
    majorLuckInterpretStatus.hidden = true;
    majorLuckInterpretStatus.textContent = "";
    majorLuckInterpretError.textContent = error instanceof Error ? error.message : "大限解讀失敗，請稍後再試。";
    majorLuckInterpretError.hidden = false;
  } finally {
    majorLuckInterpretationInFlight = false;
    updateMajorLuckInterpretButton();
  }
});

async function calculateFlowQueryFromInputs() {
  if (!currentBirthInput || flowYearInFlight) return;
  const validation = validateFlowQuery(collectFlowQuery());
  if (validation.error) {
    flowYearStatus.hidden = true;
    flowYearStatus.textContent = "";
    flowYearError.textContent = validation.error;
    flowYearError.hidden = false;
    flowYearButton.textContent = FLOW_DATE_BUTTON_TEXT;
    updateFlowYearButton();
    return;
  }
  const queryInput = validation.value;
  const requestGeneration = flowYearGeneration;
  const request = { birth_input: { ...currentBirthInput }, query: queryInput };
  flowYearInFlight = true;
  clearFlowYear();
  updateFlowYearButton();
  flowYearButton.textContent = "計算中……";
  flowYearStatus.textContent = "正在計算流年／流月／流日……";
  flowYearStatus.hidden = false;
  try {
    const response = await fetchFlowQuery(request);
    let payload = {};
    try {
      payload = await response.json();
    } catch (error) {
      if (response.ok) throw flowDateUiError("伺服器回應格式錯誤，請重試。");
    }
    if (requestGeneration !== flowYearGeneration) return;
    if (!response.ok) throw flowDateUiError(flowYearErrorMessage(response.status, payload));
    renderFlowQuery(payload, queryInput);
    flowYearStatus.hidden = true;
    flowYearStatus.textContent = "";
  } catch (error) {
    if (requestGeneration !== flowYearGeneration) return;
    flowYearStatus.hidden = true;
    flowYearStatus.textContent = "";
    flowYearError.textContent = caughtFlowDateErrorMessage(error);
    flowYearError.hidden = false;
  } finally {
    flowYearInFlight = false;
    flowYearButton.textContent = FLOW_DATE_BUTTON_TEXT;
    updateFlowYearButton();
  }
}

flowYearButton.addEventListener("click", calculateFlowQueryFromInputs);

flowYearInterpretButton.addEventListener("click", async () => {
  if (!currentBirthInput || flowYearInterpretationInFlight || currentFlowYearTarget === null) return;
  const requestGeneration = flowYearInterpretationGeneration;
  const request = {
    birth_input: { ...currentBirthInput },
    target_year: currentFlowYearTarget
  };
  flowYearInterpretationInFlight = true;
  clearFlowYearInterpretation();
  updateFlowYearInterpretButton();
  flowYearInterpretStatus.textContent = "正在解讀流年……";
  flowYearInterpretStatus.hidden = false;
  try {
    const response = await fetch("/api/flow-year/interpret", {
      method: "POST",
      headers: interpretationRequestHeaders(),
      body: JSON.stringify(request)
    });
    const payload = await response.json().catch(() => ({}));
    if (requestGeneration !== flowYearInterpretationGeneration) return;
    if (!response.ok) throw new Error(interpretationErrorMessage(response.status, payload));
    renderFlowYearInterpretation(payload);
    flowYearInterpretStatus.hidden = true;
    flowYearInterpretStatus.textContent = "";
  } catch (error) {
    if (requestGeneration !== flowYearInterpretationGeneration) return;
    flowYearInterpretStatus.hidden = true;
    flowYearInterpretStatus.textContent = "";
    flowYearInterpretError.textContent = error instanceof Error ? error.message : "流年解讀失敗，請稍後再試。";
    flowYearInterpretError.hidden = false;
  } finally {
    flowYearInterpretationInFlight = false;
    updateFlowYearInterpretButton();
  }
});

async function interpretFlowMonth() {
  if (!currentBirthInput || !currentFlowQueryInput || !currentFlowQueryResult?.flow_month || flowMonthInterpretationInFlight) return;
  const requestGeneration = flowMonthInterpretationGeneration;
  const request = { birth_input: { ...currentBirthInput }, query: { ...currentFlowQueryInput } };
  flowMonthInterpretationInFlight = true;
  clearFlowMonthInterpretation();
  updateFlowMonthInterpretButton();
  flowMonthInterpretButton.textContent = "正在解讀流月……";
  flowMonthInterpretStatus.textContent = "正在解讀流月……";
  flowMonthInterpretStatus.hidden = false;
  try {
    const response = await fetchStructuredFlowInterpretation("/api/flow-month/interpret", request);
    const payload = await response.json().catch(() => ({}));
    if (requestGeneration !== flowMonthInterpretationGeneration) return;
    if (!response.ok) throw new Error(interpretationErrorMessage(response.status, payload));
    renderFlowMonthInterpretation(payload);
    flowMonthInterpretStatus.hidden = true;
    flowMonthInterpretStatus.textContent = "";
  } catch (error) {
    if (requestGeneration !== flowMonthInterpretationGeneration) return;
    flowMonthInterpretStatus.hidden = true;
    flowMonthInterpretStatus.textContent = "";
    flowMonthInterpretError.textContent = caughtFlowInterpretationErrorMessage(error, "流月解讀");
    flowMonthInterpretError.hidden = false;
  } finally {
    flowMonthInterpretationInFlight = false;
    flowMonthInterpretButton.textContent = FLOW_MONTH_INTERPRET_BUTTON_TEXT;
    updateFlowMonthInterpretButton();
  }
}

flowMonthInterpretButton.addEventListener("click", interpretFlowMonth);

async function interpretFlowDay() {
  if (!currentBirthInput || !currentFlowQueryInput || !currentFlowQueryResult?.flow_day || flowDayInterpretationInFlight) return;
  const requestGeneration = flowDayInterpretationGeneration;
  const request = { birth_input: { ...currentBirthInput }, query: { ...currentFlowQueryInput } };
  flowDayInterpretationInFlight = true;
  clearFlowDayInterpretation();
  updateFlowDayInterpretButton();
  flowDayInterpretButton.textContent = "正在解讀流日……";
  flowDayInterpretStatus.textContent = "正在解讀流日……";
  flowDayInterpretStatus.hidden = false;
  try {
    const response = await fetchStructuredFlowInterpretation("/api/flow-day/interpret", request);
    const payload = await response.json().catch(() => ({}));
    if (requestGeneration !== flowDayInterpretationGeneration) return;
    if (!response.ok) throw new Error(interpretationErrorMessage(response.status, payload));
    renderFlowDayInterpretation(payload);
    flowDayInterpretStatus.hidden = true;
    flowDayInterpretStatus.textContent = "";
  } catch (error) {
    if (requestGeneration !== flowDayInterpretationGeneration) return;
    flowDayInterpretStatus.hidden = true;
    flowDayInterpretStatus.textContent = "";
    flowDayInterpretError.textContent = caughtFlowInterpretationErrorMessage(error, "流日解讀");
    flowDayInterpretError.hidden = false;
  } finally {
    flowDayInterpretationInFlight = false;
    flowDayInterpretButton.textContent = FLOW_DAY_INTERPRET_BUTTON_TEXT;
    updateFlowDayInterpretButton();
  }
}

flowDayInterpretButton.addEventListener("click", interpretFlowDay);

interpretButton.addEventListener("click", async () => {
  if (!currentBirthInput || interpretationInFlight) return;
  const input = { ...currentBirthInput };
  const requestGeneration = interpretationGeneration;
  interpretationInFlight = true;
  clearInterpretation();
  interpretButton.disabled = true;
  interpretStatus.textContent = "解盤中，請稍候……";
  interpretStatus.hidden = false;
  try {
    const response = await fetch("/api/interpret", {
      method: "POST",
      headers: interpretationRequestHeaders(),
      body: JSON.stringify(input)
    });
    const payload = await response.json().catch(() => ({}));
    if (requestGeneration !== interpretationGeneration) return;
    if (!response.ok) throw new Error(interpretationErrorMessage(response.status, payload));
    renderInterpretation(payload);
    currentInterpretation = payload;
    reportButton.disabled = false;
    interpretStatus.hidden = true;
    interpretStatus.textContent = "";
  } catch (error) {
    if (requestGeneration !== interpretationGeneration) return;
    interpretStatus.hidden = true;
    interpretStatus.textContent = "";
    interpretError.textContent = error instanceof Error ? error.message : "解盤失敗，請稍後再試。";
    interpretError.hidden = false;
  } finally {
    interpretationInFlight = false;
    if (requestGeneration === interpretationGeneration) {
      interpretButton.disabled = !currentBirthInput;
    }
  }
});

reportButton.addEventListener("click", async () => {
  if (!currentBirthInput || (!isStandaloneAndroid && !currentInterpretation) || reportInFlight) return;
  const requestGeneration = interpretationGeneration;
  const request = { birth_input: { ...currentBirthInput } };
  if (currentInterpretation) request.interpretation = currentInterpretation;
  if (
    currentMajorLuckInterpretation
    && currentMajorLuckInterpretationIndex !== null
    && currentMajorLuckInterpretationIndex === selectedMajorLuckIndex
  ) {
    request.major_luck_report = {
      major_luck_index: currentMajorLuckInterpretationIndex,
      interpretation: currentMajorLuckInterpretation
    };
  }
  if (
    currentFlowQueryResult
    && currentFlowQueryInput
    && currentFlowYearResult
    && currentFlowQueryResult.flow_year.target_lunar_year === currentFlowYearResult.target_lunar_year
    && currentFlowYearTarget === currentFlowYearResult.target_lunar_year
  ) {
    request.flow_query = { ...currentFlowQueryInput };
  }
  if (
    currentFlowYearInterpretation
    && request.flow_query !== undefined
    && currentFlowYearTarget === currentFlowYearInterpretation.target_year
  ) {
    request.flow_year_interpretation = currentFlowYearInterpretation;
  }
  if (currentFlowMonthInterpretation && request.flow_query !== undefined) {
    request.flow_month_interpretation = currentFlowMonthInterpretation;
  }
  if (currentFlowDayInterpretation && request.flow_query !== undefined) {
    request.flow_day_interpretation = currentFlowDayInterpretation;
  }
  reportInFlight = true;
  reportButton.disabled = true;
  reportStatus.textContent = "正在產生 Word 報告……";
  reportStatus.hidden = false;
  interpretError.hidden = true;
  interpretError.textContent = "";
  try {
    const response = await fetch("/api/report/docx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request)
    });
    if (requestGeneration !== interpretationGeneration) return;
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(response.status === 422 ? chineseError(response.status, payload) : "Word 報告產生失敗，請稍後再試。");
    }
    if (isStandaloneAndroid) {
      const saved = await response.json();
      if (!saved.saved) throw new Error("Word 報告儲存失敗。");
      reportStatus.textContent = saved.message || "Word 報告已儲存至 Downloads";
    } else {
      const blob = await response.blob();
      const filename = responseFilename(response, "Tiger-ZiWei_紫微斗數命盤.docx");
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(downloadUrl), 0);
      reportStatus.textContent = "Word 報告已產生。";
    }
  } catch (error) {
    if (requestGeneration !== interpretationGeneration) return;
    reportStatus.hidden = true;
    reportStatus.textContent = "";
    interpretError.textContent = error instanceof Error ? error.message : "Word 報告產生失敗，請稍後再試。";
    interpretError.hidden = false;
  } finally {
    reportInFlight = false;
    if (requestGeneration === interpretationGeneration) {
      reportButton.disabled = !currentBirthInput || (!isStandaloneAndroid && !currentInterpretation);
    }
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  invalidateInterpretation();
  const requestGeneration = interpretationGeneration;
  submitButton.disabled = true;
  submitButton.textContent = "排盤中…";
  try {
    const input = collectInput();
    const response = await fetch("/api/chart", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input)
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(chineseError(response.status, payload));
    if (requestGeneration !== interpretationGeneration) return;
    renderChart(payload, input);
    currentBirthInput = { ...input };
    currentChart = payload;
    interpretButton.disabled = false;
    if (isStandaloneAndroid) reportButton.disabled = false;
    updateFlowYearButton();
    updateMajorLuckInterpretButton();
    try {
      await renderChartImage(input);
    } catch (imageError) {
      imageStatus.hidden = false;
      imageStatus.textContent = imageError instanceof Error ? `命盤圖產生失敗：${imageError.message}` : "命盤圖產生失敗。";
    }
  } catch (error) {
    showError(error instanceof Error ? error.message : "排盤失敗，請稍後再試。");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "排盤";
  }
});

setBirthDateTimeShown(false);
updateFlowQueryMode();
setPreset("A");
if (isStandaloneAndroid) void loadLlmModels();
