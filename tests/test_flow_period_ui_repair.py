"""Phase 8C-R browser-facing visibility, state, and request cleanup gates."""

import json
from pathlib import Path
import shutil
import subprocess

from fastapi.testclient import TestClient
from lxml import html as lxml_html
import pytest

from app.main import app


client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


def extract_function(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated JavaScript function: {signature}")


def run_node(script: str) -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is unavailable for browser JavaScript runtime validation")
    process = subprocess.run(
        [node, "-e", script], cwd=ROOT, check=False,
        capture_output=True, text=True, encoding="utf-8", timeout=10,
    )
    assert process.returncode == 0, process.stderr
    return json.loads(process.stdout)


def test_actual_fastapi_served_assets_contain_repaired_controls_and_logic() -> None:
    html_response = client.get("/ziwei")
    js_response = client.get("/static/ziwei.js")
    css_response = client.get("/static/ziwei.css")
    assert html_response.status_code == js_response.status_code == css_response.status_code == 200
    assert html_response.headers["content-type"].startswith("text/html")
    assert "fetchStructuredFlowInterpretation" in js_response.text
    assert ".primary:disabled" in css_response.text
    assert 'id="flow-month-interpret-button"' in html_response.text
    assert 'id="flow-day-interpret-button"' in html_response.text


def test_initial_buttons_are_disabled_but_not_hidden_by_self_or_any_ancestor() -> None:
    root = lxml_html.fromstring(client.get("/ziwei").content)
    for button_id, section_id, text in (
        ("flow-month-interpret-button", "flow-month-section", "解讀流月"),
        ("flow-day-interpret-button", "flow-day-section", "解讀流日"),
    ):
        buttons = root.xpath(f'//*[@id="{button_id}"]')
        assert len(buttons) == 1
        button = buttons[0]
        assert button.text_content().strip() == text
        assert "disabled" in button.attrib
        assert not button.xpath("ancestor-or-self::*[@hidden]")
        assert button.xpath(f'ancestor::*[@id="{section_id}"]')
    assert not root.xpath('//*[@id="flow-month-section"]/@hidden')
    assert not root.xpath('//*[@id="flow-day-section"]/@hidden')


def test_disabled_button_css_keeps_text_and_background_visibly_rendered() -> None:
    css = client.get("/static/ziwei.css").text
    assert "button:disabled { cursor: not-allowed; opacity: .78; }" in css
    assert ".primary:disabled { color: #fff; background: #9b5c56; border-color: #9b5c56; }" in css
    for forbidden in (
        "#flow-month-interpret-button { display: none",
        "#flow-day-interpret-button { display: none",
        "#flow-month-section { display: none",
        "#flow-day-section { display: none",
        "opacity: 0",
    ):
        assert forbidden not in css


def test_full_javascript_initializes_without_exception_or_network_and_query_change_invalidates() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is unavailable for full JavaScript initialization validation")
    harness = r'''
const fs = require("fs");
class Element {
  constructor(id = "") {
    this.id = id; this.hidden = false; this.disabled = false; this.value = "";
    this.checked = false; this.textContent = ""; this.type = "number"; this.required = false;
    this.dataset = {}; this.listeners = {}; this.children = [];
    this.classList = { toggle() {} };
  }
  addEventListener(type, callback) { (this.listeners[type] ||= []).push(callback); }
  dispatch(type) { for (const callback of this.listeners[type] || []) callback({ preventDefault() {} }); }
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
  createElement(tag) { return new Element(tag); },
  body: get("body")
};
globalThis.URL = { createObjectURL() { return "blob:test"; }, revokeObjectURL() {} };
let fetchCalls = 0;
globalThis.fetch = async () => { fetchCalls += 1; throw new Error("unexpected automatic fetch"); };
const source = fs.readFileSync("app/static/ziwei.js", "utf8");
const appended = `
const initial = {
  monthDisabled: flowMonthInterpretButton.disabled,
  dayDisabled: flowDayInterpretButton.disabled,
  monthSectionHidden: document.querySelector("#flow-month-section").hidden,
  daySectionHidden: document.querySelector("#flow-day-section").hidden,
  fetchCalls
};
currentBirthInput = { name: "Case A" };
currentFlowQueryInput = { mode: "lunar", year: 2026, month: 10, day: 7, is_leap_month: false };
currentFlowQueryResult = { flow_month: {}, flow_day: {} };
currentFlowMonthInterpretation = { overview: "old month" };
currentFlowDayInterpretation = { overview: "old day" };
flowMonthInterpretationResult.hidden = false;
flowDayInterpretationResult.hidden = false;
updateFlowMonthInterpretButton(); updateFlowDayInterpretButton();
const beforeChange = { monthDisabled: flowMonthInterpretButton.disabled, dayDisabled: flowDayInterpretButton.disabled };
document.querySelector("#target-lunar-month").dispatch("input");
const afterChange = {
  monthDisabled: flowMonthInterpretButton.disabled,
  dayDisabled: flowDayInterpretButton.disabled,
  monthInterpretation: currentFlowMonthInterpretation,
  dayInterpretation: currentFlowDayInterpretation,
  monthResultHidden: flowMonthInterpretationResult.hidden,
  dayResultHidden: flowDayInterpretationResult.hidden,
  flowResult: currentFlowQueryResult,
  fetchCalls
};
process.stdout.write(JSON.stringify({ initial, beforeChange, afterChange }));`;
eval(source + appended);
'''
    result = run_node(harness)
    assert result["initial"] == {
        "monthDisabled": True, "dayDisabled": True,
        "monthSectionHidden": False, "daySectionHidden": False, "fetchCalls": 0,
    }
    assert result["beforeChange"] == {"monthDisabled": False, "dayDisabled": False}
    assert result["afterChange"] == {
        "monthDisabled": True, "dayDisabled": True,
        "monthInterpretation": None, "dayInterpretation": None,
        "monthResultHidden": True, "dayResultHidden": True,
        "flowResult": None, "fetchCalls": 0,
    }


def test_authoritative_result_granularity_alone_controls_button_enablement() -> None:
    javascript = client.get("/static/ziwei.js").text
    month_update = extract_function(javascript, "function updateFlowMonthInterpretButton()")
    day_update = extract_function(javascript, "function updateFlowDayInterpretButton()")
    script = f'''
let currentBirthInput = {{ name: "Case A" }};
let currentFlowQueryResult = null;
let flowMonthInterpretationInFlight = false;
let flowDayInterpretationInFlight = false;
let flowMonthInterpretButton = {{ disabled: false }};
let flowDayInterpretButton = {{ disabled: false }};
{month_update}
{day_update}
const cases = [];
for (const result of [
  {{ flow_year: {{}} }},
  {{ flow_year: {{}}, flow_month: {{}}, flow_day: null }},
  {{ flow_year: {{}}, flow_month: {{}}, flow_day: {{}} }},
  {{ flow_year: {{}}, flow_month: {{}}, flow_day: {{}} }}
]) {{
  currentFlowQueryResult = result;
  updateFlowMonthInterpretButton(); updateFlowDayInterpretButton();
  cases.push([flowMonthInterpretButton.disabled, flowDayInterpretButton.disabled]);
}}
process.stdout.write(JSON.stringify(cases));
'''
    assert run_node(script) == [
        [True, True],
        [False, True],
        [False, False],
        [False, False],
    ]


@pytest.mark.parametrize(
    "layer,handler_name,button_text,endpoint",
    (
        ("Month", "interpretFlowMonth", "解讀流月", "/api/flow-month/interpret"),
        ("Day", "interpretFlowDay", "解讀流日", "/api/flow-day/interpret"),
    ),
)
def test_click_calls_exact_endpoint_once_and_always_restores_button(
    layer, handler_name, button_text, endpoint
) -> None:
    javascript = client.get("/static/ziwei.js").text
    handler = extract_function(javascript, f"async function {handler_name}()")
    in_flight = f"flow{layer}InterpretationInFlight"
    generation = f"flow{layer}InterpretationGeneration"
    button = f"flow{layer}InterpretButton"
    status = f"flow{layer}InterpretStatus"
    error = f"flow{layer}InterpretError"
    clear = f"clearFlow{layer}Interpretation"
    update = f"updateFlow{layer}InterpretButton"
    render = f"renderFlow{layer}Interpretation"
    result_key = "flow_month" if layer == "Month" else "flow_day"
    constant = f"FLOW_{layer.upper()}_INTERPRET_BUTTON_TEXT"
    script = f'''
const {constant} = {json.dumps(button_text, ensure_ascii=False)};
let currentBirthInput = {{ name: "Case A" }};
let currentFlowQueryInput = {{ mode: "solar", year: 2029, month: 2, day: 13 }};
let currentFlowQueryResult = {{ {result_key}: {{}} }};
let {in_flight} = false;
let {generation} = 0;
let {button} = {{ disabled: false, textContent: {constant} }};
let {status} = {{ hidden: true, textContent: "" }};
let {error} = {{ hidden: true, textContent: "" }};
let scenario = "success";
let calls = [];
let renderCalls = 0;
function {clear}() {{ {status}.hidden = true; {status}.textContent = ""; {error}.hidden = true; {error}.textContent = ""; }}
function {update}() {{ {button}.disabled = {in_flight} || !currentBirthInput || !currentFlowQueryResult?.{result_key}; }}
function {render}(payload) {{ if (!payload.valid) throw new Error("malformed response"); renderCalls += 1; }}
function interpretationErrorMessage(status) {{ return `HTTP ${{status}}`; }}
function caughtFlowInterpretationErrorMessage(error, layer) {{
  if (error instanceof Error && error.name === "AbortError") return `${{layer}}逾時，請重試。`;
  if (error instanceof TypeError) return "網路連線失敗，請重試。";
  return error instanceof Error ? error.message : `${{layer}}失敗，請稍後再試。`;
}}
async function fetchStructuredFlowInterpretation(url) {{
  calls.push(url);
  if (scenario === "network") throw new TypeError("network");
  if (scenario === "timeout") {{ const e = new Error("timeout"); e.name = "AbortError"; throw e; }}
  if (scenario === "malformed") return {{ ok: true, status: 200, json: async () => {{ throw new Error("bad json"); }} }};
  if (scenario === "422") return {{ ok: false, status: 422, json: async () => ({{}}) }};
  if (scenario === "500") return {{ ok: false, status: 500, json: async () => ({{}}) }};
  return {{ ok: true, status: 200, json: async () => ({{ valid: true }}) }};
}}
{handler}
function snapshot() {{ return {{ inFlight: {in_flight}, disabled: {button}.disabled, text: {button}.textContent, statusHidden: {status}.hidden, error: {error}.hidden ? "" : {error}.textContent, calls: [...calls], renderCalls }}; }}
(async () => {{
  const results = {{}};
  for (const name of ["success", "422", "500", "network", "timeout", "malformed"]) {{
    scenario = name; calls = []; renderCalls = 0; {in_flight} = false; {button}.textContent = {constant};
    await {handler_name}(); results[name] = snapshot();
  }}
  calls = []; {in_flight} = true; await {handler_name}(); results.duplicate = snapshot(); {in_flight} = false;
  process.stdout.write(JSON.stringify(results));
}})();
'''
    results = run_node(script)
    for scenario in ("success", "422", "500", "network", "timeout", "malformed"):
        state = results[scenario]
        assert state["inFlight"] is False
        assert state["disabled"] is False
        assert state["text"] == button_text
        assert state["statusHidden"] is True
        assert state["calls"] == [endpoint]
    assert results["success"]["renderCalls"] == 1
    assert results["malformed"]["renderCalls"] == 0
    assert results["duplicate"]["calls"] == []


def test_interpretation_fetch_timeout_aborts_and_cleans_timer() -> None:
    javascript = client.get("/static/ziwei.js").text
    helper = extract_function(javascript, "async function fetchStructuredFlowInterpretation")
    script = f'''
let aborted = false;
globalThis.fetch = (_url, options) => new Promise((_resolve, reject) => {{
  options.signal.addEventListener("abort", () => {{
    aborted = true; const error = new Error("aborted"); error.name = "AbortError"; reject(error);
  }});
}});
{helper}
(async () => {{
  try {{ await fetchStructuredFlowInterpretation("/api/flow-month/interpret", {{}}, 10); }}
  catch (error) {{ process.stdout.write(JSON.stringify({{ aborted, name: error.name }})); }}
}})();
'''
    assert run_node(script) == {"aborted": True, "name": "AbortError"}


def test_no_automatic_interpretation_fetch_in_initialization_or_calculation_paths() -> None:
    javascript = client.get("/static/ziwei.js").text
    month_calls = javascript.count('fetchStructuredFlowInterpretation("/api/flow-month/interpret"')
    day_calls = javascript.count('fetchStructuredFlowInterpretation("/api/flow-day/interpret"')
    assert month_calls == day_calls == 1
    calculate = javascript[
        javascript.index("async function calculateFlowQueryFromInputs"):
        javascript.index("async function interpretFlowMonth")
    ]
    report = javascript[javascript.index('reportButton.addEventListener("click"'):]
    for endpoint in ("/api/flow-month/interpret", "/api/flow-day/interpret"):
        assert endpoint not in calculate
        assert endpoint not in report
