"use strict";
const fs = require("fs");
const assert = require("assert/strict");
class Element {
  constructor(id = "") {
    this.id = id; this.hidden = false; this.disabled = false; this.value = "";
    this.checked = false; this.textContent = ""; this.type = "number"; this.required = false;
    this.dataset = {}; this.listeners = {}; this.children = [];
    this.classList = { toggle() {} };
  }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  async dispatch(type) { for (const fn of this.listeners[type] || []) await fn({ preventDefault() {} }); }
  replaceChildren(...children) { this.children = children; }
  append(...children) { this.children.push(...children); }
  appendChild(child) { this.children.push(child); return child; }
  remove() {}
  querySelector(selector) { return get(`${this.id}:${selector}`); }
  setAttribute(name, value) { this[name] = value; }
  removeAttribute(name) { delete this[name]; }
}
const elements = new Map();
function get(id) { if (!elements.has(id)) elements.set(id, new Element(id)); return elements.get(id); }
const calendarSolar = get("calendar-solar"); calendarSolar.value = "solar"; calendarSolar.checked = true;
const calendarLunar = get("calendar-lunar"); calendarLunar.value = "lunar";
const flowSolar = get("flow-query-solar"); flowSolar.value = "solar"; flowSolar.checked = true;
const flowLunar = get("flow-query-lunar"); flowLunar.value = "lunar";
globalThis.window = globalThis;
globalThis.location = { origin: "https://appassets.androidplatform.net" };
globalThis.document = {
  querySelector(selector) {
    if (selector === 'input[name="calendar_type"]:checked') return calendarSolar.checked ? calendarSolar : calendarLunar;
    if (selector === 'input[name="flow_query_mode"]:checked') return flowSolar.checked ? flowSolar : flowLunar;
    return get(selector.startsWith("#") ? selector.slice(1) : selector);
  },
  querySelectorAll(selector) {
    if (selector === 'input[name="calendar_type"]') return [calendarSolar, calendarLunar];
    if (selector === 'input[name="flow_query_mode"]') return [flowSolar, flowLunar];
    return [];
  },
  createElement(tag) { return new Element(tag); }, body: get("body")
};
let unexpectedNetworkCalls = 0;
globalThis.fetch = async () => { unexpectedNetworkCalls += 1; throw new Error("external network forbidden"); };
const nativeCalls = [];
globalThis.TigerAndroid = {
  request(id, action, raw) {
    const envelope = JSON.parse(raw);
    nativeCalls.push({ action, envelope });
    let success = true;
    let value;
    if (action === "get_models") value = [{ id: "z-ai/glm-5.3-flash", display_name: "GLM-5.3-Flash", default: true }, { id: "openai/gpt-oss-20b", display_name: "GPT-OSS-20B", default: false }];
    else if (action === "generate_docx") {
      const request = JSON.parse(envelope.body);
      assert(!Object.hasOwn(request, "interpretation"));
      assert(!Object.hasOwn(envelope.headers, "X-Tiger-NVIDIA-API-Key"));
      value = { saved: true, filename: "Tiger_紫微斗數命盤.docx", message: "Word 報告已儲存至 Downloads" };
    } else if (action === "interpret_natal") { success = false; value = { status: 401, detail: "請輸入 NVIDIA API KEY。" }; }
    else throw new Error(`unexpected native action ${action}`);
    setImmediate(() => globalThis.TigerStandalone.onResponse(id, success, JSON.stringify(value)));
  }
};
const source = fs.readFileSync("app/static/ziwei.js", "utf8");
const appended = `
(async () => {
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(aiModelSelect.children.length, 2);
  const birthMasked = birthDateTimeInputs.every((input) => input.type === "password");
  assert.equal(nvidiaApiKeyInput.value, "");
  setBirthDateTimeShown(true); assert(birthDateTimeInputs.every((input) => input.type === "number"));
  setBirthDateTimeShown(false);
  const chart = { immutable: "chart" }, flow = { immutable: "flow" };
  currentBirthInput = { name: "Tiger" }; currentChart = chart; currentFlowQueryResult = flow;
  currentInterpretation = { overview: "old" }; currentMajorLuckInterpretation = { overview: "old" };
  currentFlowYearInterpretation = { overview: "old" }; currentFlowMonthInterpretation = { overview: "old" }; currentFlowDayInterpretation = { overview: "old" };
  const beforeChange = nativeCalls.length;
  invalidateAiInterpretationsForModelChange();
  assert.equal(nativeCalls.length, beforeChange);
  const modelChangePreservesFacts = currentChart === chart && currentFlowQueryResult === flow;
  assert.equal(currentInterpretation, null); assert.equal(currentMajorLuckInterpretation, null);
  assert.equal(currentFlowYearInterpretation, null); assert.equal(currentFlowMonthInterpretation, null); assert.equal(currentFlowDayInterpretation, null);
  const offlineWordEnabled = !reportButton.disabled;
  currentFlowQueryResult = null;
  await reportButton.dispatch("click");
  const docxSaved = reportStatus.textContent === "Word 報告已儲存至 Downloads";
  const ai = await fetch("/api/interpret", { method: "POST", body: "{}" });
  const blankKeyMessage = interpretationErrorMessage(ai.status, await ai.json());
  let unknownActionRejected = false;
  try { await fetch("https://untrusted.example/arbitrary"); } catch (_error) { unknownActionRejected = true; }
  const receipt = { offlineWordEnabled, birthMasked, modelChangePreservesFacts, unknownActionRejected, blankKeyMessage, docxSaved, unexpectedNetworkCalls };
  process.stdout.write(JSON.stringify(receipt));
})().catch((error) => { process.stderr.write(String(error.stack)); process.exitCode = 1; });`;
eval(source + appended);
