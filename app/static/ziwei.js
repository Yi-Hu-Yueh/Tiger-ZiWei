"use strict";

const presets = {
  A: { name: "預設 A", gender: "female", birth_year: 2025, birth_month: 1, birth_day: 29, birth_hour: 0, birth_minute: 30, birthplace: "Taipei" },
  B: { name: "預設 B", gender: "female", birth_year: 2025, birth_month: 1, birth_day: 29, birth_hour: 1, birth_minute: 30, birthplace: "Taipei" },
  C: { name: "預設 C", gender: "female", birth_year: 2024, birth_month: 2, birth_day: 29, birth_hour: 12, birth_minute: 0, birthplace: "Taipei" },
  L: { name: "預設 L", gender: "female", birth_year: 2025, birth_month: 7, birth_day: 25, birth_hour: 12, birth_minute: 0, birthplace: "Taipei" },
  Z: { name: "預設 Z", gender: "female", birth_year: 2025, birth_month: 7, birth_day: 24, birth_hour: 23, birth_minute: 59, birthplace: "Taipei" }
};

const form = document.querySelector("#chart-form");
const resultSection = document.querySelector("#result");
const errorBox = document.querySelector("#error-message");
const submitButton = document.querySelector("#submit-button");
const chartImage = document.querySelector("#chart-image");
const chartImageWrap = document.querySelector("#chart-image-wrap");
const chartDownload = document.querySelector("#chart-download");
const chartFullsize = document.querySelector("#chart-fullsize");
const chartImageLink = document.querySelector("#chart-image-link");
const imageStatus = document.querySelector("#image-status");
let chartImageUrl = null;

function setPreset(key) {
  const preset = presets[key];
  if (!preset) return;
  Object.entries(preset).forEach(([field, value]) => {
    const control = document.querySelector(`#${field}`);
    if (control) control.value = value;
  });
  clearError();
}

function collectInput() {
  const value = (id) => document.querySelector(`#${id}`).value;
  const name = value("name").trim();
  return {
    name: name || null,
    gender: value("gender"),
    birth_year: Number(value("birth_year")),
    birth_month: Number(value("birth_month")),
    birth_day: Number(value("birth_day")),
    birth_hour: Number(value("birth_hour")),
    birth_minute: Number(value("birth_minute")),
    birthplace: value("birthplace").trim()
  };
}

function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
  resultSection.hidden = true;
}

function chineseError(status, payload) {
  if (status === 422) {
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

function renderSummary(chart) {
  const container = document.querySelector("#summary");
  container.replaceChildren();
  const birth = chart.birth_data;
  const calendar = chart.calendar;
  const lunar = calendar.lunar_date;
  const layout = chart.palace_layout;
  const lifePalace = chart.palaces.find((palace) => palace.is_life_palace);
  const bodyPalace = chart.palaces.find((palace) => palace.has_body_palace);
  const lunarText = `${lunar.year} 年${lunar.is_leap_month ? "閏" : ""}${lunarMonthText(lunar.month)}月${lunarDayText(lunar.day)}`;

  addSummary("姓名", birth.name || "未填寫");
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

function renderChart(chart) {
  renderSummary(chart);
  renderPalaces(chart);
  renderTransformations(chart);
  resultSection.hidden = false;
  resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function responseFilename(response) {
  const disposition = response.headers.get("Content-Disposition") || "";
  const encoded = disposition.match(/filename\*=utf-8''([^;]+)/i);
  if (encoded) return decodeURIComponent(encoded[1]);
  const plain = disposition.match(/filename="?([^";]+)"?/i);
  return plain ? plain[1] : "Tiger-ZiWei_紫微命盤.png";
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

document.querySelectorAll(".preset").forEach((button) => {
  button.addEventListener("click", () => setPreset(button.dataset.preset));
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
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
    renderChart(payload);
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

setPreset("A");
