"""Phase 8B deterministic Flow-Date, Flow-Month, and Flow-Day contracts."""

from datetime import date, time
import inspect
import json
from pathlib import Path
import shutil
import subprocess

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.birth_input import normalize_birth_input
from app.calendar.ganzhi import calculate_civil_calendar
from app.main import app
from app.models.birth import BirthInput
from app.models.calendar import EARTHLY_BRANCHES
from app.models.flow_date import FlowDateInput
from app.ziwei import calculate_basic_chart
from app.ziwei.flow_date import (
    calculate_flow_date,
    effective_lunar_month,
    flow_day_life_branch,
    flow_month_life_branch,
)
import app.ziwei.flow_date as flow_date_module


client = TestClient(app)
SOLAR_A = {
    "name": "Case A", "gender": "female", "calendar_type": "solar",
    "birth_year": 2025, "birth_month": 1, "birth_day": 29,
    "birth_hour": 0, "birth_minute": 30, "birthplace": "Taipei",
}
LUNAR_A = {
    "name": "Case A", "gender": "female", "calendar_type": "lunar",
    "lunar_year": 2025, "lunar_month": 1, "lunar_day": 1,
    "is_leap_month": False, "birth_hour": 0, "birth_minute": 30,
    "birthplace": "Taipei",
}
SOLAR_L = {
    "name": "Case L", "gender": "female", "calendar_type": "solar",
    "birth_year": 2025, "birth_month": 7, "birth_day": 25,
    "birth_hour": 12, "birth_minute": 0, "birthplace": "Taipei",
}
LUNAR_L = {
    "name": "Case L", "gender": "female", "calendar_type": "lunar",
    "lunar_year": 2025, "lunar_month": 6, "lunar_day": 1,
    "is_leap_month": True, "birth_hour": 12, "birth_minute": 0,
    "birthplace": "Taipei",
}
TARGET_A = FlowDateInput(year=2029, month=2, day=13, hour=12, minute=0)


def chart(payload=SOLAR_A):
    return calculate_basic_chart(normalize_birth_input(BirthInput.model_validate(payload)))


def calculate(payload=SOLAR_A, target=TARGET_A):
    return calculate_flow_date(chart(payload), target)


def test_low_level_case_a_flow_month_static_fixture() -> None:
    assert flow_month_life_branch("酉", "子", 1, 1) == "酉"
    assert flow_month_life_branch("酉", "子", 1, 2) == "戌"


@pytest.mark.parametrize("hour_index", range(12))
def test_flow_month_formula_covers_every_birth_hour_branch(hour_index: int) -> None:
    expected = EARTHLY_BRANCHES[(9 + hour_index + 4 - 2) % 12]
    assert flow_month_life_branch("酉", EARTHLY_BRANCHES[hour_index], 2, 4) == expected


def test_flow_month_progression_and_wrap_are_explicit() -> None:
    assert [flow_month_life_branch("酉", "子", 1, month) for month in range(1, 5)] == [
        "酉", "戌", "亥", "子",
    ]


@pytest.mark.parametrize(
    ("lunar_day", "expected"),
        ((1, "酉"), (2, "戌"), (3, "亥"), (4, "子"), (12, "申"), (13, "酉"), (30, "寅")),
)
def test_flow_day_static_progression_and_wrap(lunar_day: int, expected: str) -> None:
    assert flow_day_life_branch("酉", lunar_day) == expected


def test_representative_case_a_target_is_authoritatively_verified() -> None:
    result = calculate()
    assert (
        result.target_lunar_year,
        result.target_lunar_month,
        result.target_lunar_day,
        result.target_is_leap_month,
    ) == (2029, 1, 1, False)
    assert result.flow_year.ganzhi.display == "己酉"
    assert result.flow_month.flow_month_life_palace_branch == "酉"
    assert result.flow_day.flow_day_life_palace_branch == "酉"


def test_second_gregorian_day_advances_only_flow_day_life_palace() -> None:
    first = calculate()
    second = calculate(target=FlowDateInput(year=2029, month=2, day=14, hour=12, minute=0))
    assert (first.target_lunar_day, second.target_lunar_day) == (1, 2)
    assert first.flow_month.flow_month_life_palace_branch == second.flow_month.flow_month_life_palace_branch == "酉"
    assert second.flow_day.flow_day_life_palace_branch == "戌"


def test_flow_month_and_day_have_twelve_unique_host_locked_palaces() -> None:
    natal = chart()
    result = calculate_flow_date(natal, TARGET_A)
    hosts = {palace.earthly_branch: palace for palace in natal.palaces}
    for layer in (result.flow_month, result.flow_day):
        assert len(layer.palaces) == 12
        assert len({item.earthly_branch for item in layer.palaces}) == 12
        for item in layer.palaces:
            assert item.natal_palace_name == hosts[item.earthly_branch].palace_name
            assert item.natal_palace_ganzhi == hosts[item.earthly_branch].palace_ganzhi


def test_target_day_ganzhi_reuses_authoritative_calendar_engine() -> None:
    result = calculate()
    calendar = calculate_civil_calendar(date(2029, 2, 13), time(12, 0))
    assert result.flow_month.month_ganzhi == calendar.month_ganzhi
    assert result.flow_day.day_ganzhi == calendar.day_ganzhi


def test_late_zi_target_does_not_advance_civil_or_lunar_day() -> None:
    before = calculate(target=FlowDateInput(year=2029, month=2, day=13, hour=22, minute=59))
    late_zi = calculate(target=FlowDateInput(year=2029, month=2, day=13, hour=23, minute=30))
    assert before.target_solar_datetime.date() == late_zi.target_solar_datetime.date() == date(2029, 2, 13)
    assert before.target_lunar_day == late_zi.target_lunar_day == 1
    assert before.flow_day == late_zi.flow_day


def test_whole_leap_month_convention_applies_to_birth_and_target() -> None:
    assert effective_lunar_month(6, False) == 6
    assert effective_lunar_month(6, True) == 7
    case_a_target = calculate(target=FlowDateInput(year=2025, month=7, day=25, hour=12, minute=0))
    assert (
        case_a_target.target_lunar_month,
        case_a_target.target_is_leap_month,
        case_a_target.target_effective_month,
    ) == (6, True, 7)
    case_l_target = calculate(SOLAR_L, FlowDateInput(year=2025, month=7, day=25, hour=12, minute=0))
    assert chart(SOLAR_L).palace_layout.effective_lunar_month == 7
    assert case_l_target.flow_month.effective_month == 7


@pytest.mark.parametrize("solar,lunar", ((SOLAR_A, LUNAR_A), (SOLAR_L, LUNAR_L)))
def test_equivalent_solar_and_lunar_birth_inputs_produce_identical_layers(solar: dict, lunar: dict) -> None:
    target = TARGET_A
    assert calculate(solar, target).flow_year == calculate(lunar, target).flow_year
    assert calculate(solar, target).flow_month == calculate(lunar, target).flow_month
    assert calculate(solar, target).flow_day == calculate(lunar, target).flow_day


def test_gregorian_january_uses_derived_previous_lunar_year() -> None:
    result = calculate(target=FlowDateInput(year=2026, month=1, day=1, hour=12, minute=0))
    assert result.target_lunar_year == 2025
    assert result.flow_year.target_lunar_year == 2025


def test_equal_birth_datetime_is_valid_and_earlier_target_is_rejected() -> None:
    equal = calculate(target=FlowDateInput(year=2025, month=1, day=29, hour=0, minute=30))
    assert equal.target_solar_datetime.isoformat(timespec="minutes") == "2025-01-29T00:30"
    with pytest.raises(ValueError, match="earlier"):
        calculate(target=FlowDateInput(year=2025, month=1, day=29, hour=0, minute=29))


@pytest.mark.parametrize(
    "values",
    (
        {"year": 2029, "month": 2, "day": 30, "hour": 12, "minute": 0},
        {"year": 1582, "month": 10, "day": 14, "hour": 12, "minute": 0},
        {"year": 2029, "month": 1, "day": 1, "hour": 24, "minute": 0},
        {"year": 2029, "month": 1, "day": 1, "hour": 0, "minute": 60},
    ),
)
def test_invalid_target_datetime_is_rejected(values: dict) -> None:
    with pytest.raises(ValidationError):
        FlowDateInput.model_validate(values)


def test_flow_date_has_no_system_date_dependency() -> None:
    source = inspect.getsource(flow_date_module)
    assert "datetime.now" not in source
    assert "date.today" not in source
    assert "while " not in source
    for network_dependency in ("httpx", "requests", "nvidia", "await "):
        assert network_dependency not in source.lower()


def test_flow_date_api_returns_all_layers_and_never_calls_nvidia(monkeypatch) -> None:
    async def forbidden(*args, **kwargs):
        raise AssertionError("Flow-Date must never call NVIDIA")

    monkeypatch.setattr("app.llm.nvidia_client.NvidiaClient.chat", forbidden)
    response = client.post(
        "/api/flow-date",
        json={"birth_input": SOLAR_A, "target_datetime": TARGET_A.model_dump()},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["target_solar_datetime"] == "2029-02-13T12:00:00"
    assert "".join(payload["flow_year"]["ganzhi"].values()) == "己酉"
    assert "".join(payload["flow_month"]["month_ganzhi"].values()) == "丙寅"
    assert payload["flow_month"]["flow_month_life_palace_branch"] == "酉"
    assert "".join(payload["flow_day"]["day_ganzhi"].values()) == "甲戌"
    assert payload["flow_day"]["flow_day_life_palace_branch"] == "酉"
    assert len(payload["flow_month"]["palaces"]) == 12
    assert len(payload["flow_day"]["palaces"]) == 12


@pytest.mark.parametrize("missing_field", ("year", "month", "day", "hour", "minute"))
def test_flow_date_api_quickly_rejects_each_missing_target_field(missing_field: str) -> None:
    target = TARGET_A.model_dump()
    target.pop(missing_field)
    response = client.post(
        "/api/flow-date",
        json={"birth_input": SOLAR_A, "target_datetime": target},
    )
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.parametrize("blank_field", ("year", "month", "day", "hour", "minute"))
def test_flow_date_api_quickly_rejects_each_blank_target_field(blank_field: str) -> None:
    target = TARGET_A.model_dump()
    target[blank_field] = ""
    response = client.post(
        "/api/flow-date",
        json={"birth_input": SOLAR_A, "target_datetime": target},
    )
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_flow_date_api_rejects_bad_or_prebirth_targets() -> None:
    invalid = client.post(
        "/api/flow-date",
        json={
            "birth_input": SOLAR_A,
            "target_datetime": {"year": 2029, "month": 2, "day": 30, "hour": 12, "minute": 0},
        },
    )
    assert invalid.status_code == 422
    prebirth = client.post(
        "/api/flow-date",
        json={
            "birth_input": SOLAR_A,
            "target_datetime": {"year": 2024, "month": 1, "day": 1, "hour": 12, "minute": 0},
        },
    )
    assert prebirth.status_code == 422
    assert prebirth.json()["detail"]["code"] == "INVALID_FLOW_DATE"


def test_openapi_exposes_flow_date_endpoint() -> None:
    assert "post" in client.get("/openapi.json").json()["paths"]["/api/flow-date"]


def test_pinned_iztro_non_leap_secondary_comparison() -> None:
    root = Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    receipt = root / "tmp/phase1f-iztro/build-receipt.json"
    if not node or not receipt.exists():
        pytest.skip("pinned iztro development engine/Node absent")
    process = subprocess.run(
        [node, "tests/verify_iztro_flow_date.cjs"], cwd=root, check=False,
        capture_output=True, text=True, encoding="utf-8",
    )
    assert process.returncode == 0, process.stderr + process.stdout
    external = json.loads(process.stdout)
    assert external["revision"] == "2c7ef9be669df7b19d1799f4dce335fed3794f78"
    for index, target in enumerate(
        (
            FlowDateInput(year=2029, month=2, day=13, hour=12, minute=0),
            FlowDateInput(year=2029, month=2, day=14, hour=12, minute=0),
        )
    ):
        expected = external["results"][index]
        actual = calculate(target=target)
        assert expected["flowYearBranch"] == actual.flow_year.flow_life_palace_branch
        assert expected["flowMonthLifeBranch"] == actual.flow_month.flow_month_life_palace_branch
        assert expected["flowDayLifeBranch"] == actual.flow_day.flow_day_life_palace_branch
        assert expected["monthGanzhi"] == actual.flow_month.month_ganzhi.display
        assert expected["dayGanzhi"] == actual.flow_day.day_ganzhi.display
    assert external["differentConvention"]


def test_flow_query_ui_has_modes_readable_dates_and_no_target_time() -> None:
    html = client.get("/ziwei").text
    for field in (
        "target-solar-year", "target-solar-month", "target-solar-day",
        "target-lunar-year", "target-lunar-month", "target-lunar-day",
    ):
        assert f'id="{field}" type="number"' in html
        field_markup = html[html.index(f'id="{field}"'):]
        assert 'type="password"' not in field_markup[:180]
    assert 'id="flow-date-fields" class="flow-date-fields"' in html
    assert 'id="flow-date-toggle"' not in html
    assert 'id="target-hour"' not in html
    assert 'id="target-minute"' not in html
    assert 'name="flow_query_mode"' in html
    assert 'id="target-is-leap-month"' in html
    assert "顯示運限年月日時分" not in html
    assert "隱藏運限年月日時分" not in html
    assert "計算流年／流月／流日" in html
    for element in (
        'id="flow-year-summary"', 'id="flow-year-body"',
        'id="flow-month-summary"', 'id="flow-month-body"',
        'id="flow-day-summary"', 'id="flow-day-body"',
    ):
        assert element in html


def test_flow_date_has_no_masking_or_toggle_logic() -> None:
    javascript = client.get("/static/ziwei.js").text
    for removed in (
        "flowDateToggle", "flowDateTimeShown", "setFlowDateTimeShown",
        "顯示運限年月日時分", "隱藏運限年月日時分",
    ):
        assert removed not in javascript


def test_target_edit_invalidates_every_dynamic_layer_and_calculation_has_no_ai_call() -> None:
    javascript = client.get("/static/ziwei.js").text
    listener = javascript[javascript.index("flowQueryInputs.forEach"):javascript.index("majorLuckSelect.addEventListener")]
    assert 'input.addEventListener(input === flowLeapMonthInput ? "change" : "input"' in listener
    assert "invalidateFlowYear();" in listener
    clear = javascript[javascript.index("function clearFlowYear()"):javascript.index("function updateFlowYearButton()")]
    for state in (
        "currentFlowQueryResult = null", "currentFlowYearResult = null",
        'document.querySelector("#flow-month-body").replaceChildren()',
        'document.querySelector("#flow-day-body").replaceChildren()',
        "invalidateFlowYearInterpretation();",
    ):
        assert state in clear
    calculate_handler = javascript[javascript.index("async function calculateFlowQueryFromInputs"):javascript.index('flowYearInterpretButton.addEventListener("click"')]
    assert "fetchFlowQuery(request)" in calculate_handler
    assert 'fetch("/api/interpret"' not in calculate_handler
    assert 'fetch("/api/major-luck/interpret"' not in calculate_handler
    assert 'fetch("/api/flow-year/interpret"' not in calculate_handler


def test_flow_date_client_validation_runtime_covers_missing_and_invalid_values() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is unavailable for the frontend validator runtime test")
    javascript = client.get("/static/ziwei.js").text
    validator = javascript[
        javascript.index("function validateFlowQuery"):
        javascript.index("function flowDateUiError")
    ]
    cases = (
        {"mode": "solar", "year": "2026", "month": "", "day": ""},
        {"mode": "solar", "year": "2026", "month": "10", "day": ""},
        {"mode": "solar", "year": "2026", "month": "13", "day": "1"},
        {"mode": "solar", "year": "2026", "month": "2", "day": "30"},
        {"mode": "lunar", "year": "2026", "month": "", "day": "7", "is_leap_month": False},
        {"mode": "lunar", "year": "2026", "month": "", "day": "", "is_leap_month": True},
        {"mode": "lunar", "year": "2026", "month": "10", "day": "", "is_leap_month": False},
        {"mode": "solar", "year": "2029", "month": "2", "day": "13"},
    )
    script = (
        validator
        + "\nconst cases = "
        + json.dumps(cases, ensure_ascii=False)
        + ";\nprocess.stdout.write(JSON.stringify(cases.map(validateFlowQuery)));"
    )
    process = subprocess.run(
        [node, "-e", script], check=False, capture_output=True, text=True, encoding="utf-8",
    )
    assert process.returncode == 0, process.stderr
    results = json.loads(process.stdout)
    assert results[0]["error"] == "國曆查詢請完整輸入年、月、日。"
    assert results[1]["error"] == "國曆查詢請完整輸入年、月、日。"
    assert results[2]["error"] == "請輸入有效的國曆日期。"
    assert results[3]["error"] == "請輸入有效的國曆日期。"
    assert results[4]["error"] == "農曆日必須搭配農曆月。"
    assert results[5]["error"] == "閏月設定必須搭配農曆月。"
    assert results[6] == {
        "error": None,
        "value": {"mode": "lunar", "year": 2026, "month": 10, "is_leap_month": False},
    }
    assert results[7] == {
        "error": None,
        "value": {"mode": "solar", "year": 2029, "month": 2, "day": 13},
    }


def test_flow_date_timeout_runtime_aborts_never_resolving_fetch() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is unavailable for the frontend timeout runtime test")
    javascript = client.get("/static/ziwei.js").text
    fetch_helper = javascript[
        javascript.index("async function fetchFlowQuery"):
        javascript.index("function clearError")
    ]
    script = f"""
let aborted = false;
globalThis.fetch = (_url, options) => new Promise((_resolve, reject) => {{
  options.signal.addEventListener("abort", () => {{
    aborted = true;
    const error = new Error("aborted");
    error.name = "AbortError";
    reject(error);
  }});
}});
{fetch_helper}
(async () => {{
  try {{
    await fetchFlowQuery({{}}, 10);
  }} catch (error) {{
    process.stdout.write(JSON.stringify({{ aborted, name: error.name }}));
  }}
}})();
"""
    process = subprocess.run(
        [node, "-e", script], check=False, capture_output=True, text=True, encoding="utf-8",
        timeout=5,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == {"aborted": True, "name": "AbortError"}


def test_flow_date_click_handler_validates_before_loading_and_always_cleans_up() -> None:
    javascript = client.get("/static/ziwei.js").text
    handler = javascript[
        javascript.index("async function calculateFlowQueryFromInputs"):
        javascript.index('flowYearButton.addEventListener("click"')
    ]
    validation_index = handler.index("validateFlowQuery(collectFlowQuery())")
    loading_index = handler.index("flowYearInFlight = true")
    fetch_index = handler.index("fetchFlowQuery(request)")
    assert validation_index < loading_index < fetch_index
    assert "if (!currentBirthInput || flowYearInFlight) return" in handler
    assert "國曆查詢請完整輸入年、月、日。" in javascript
    assert 'flowYearButton.textContent = "計算中……"' in handler
    finally_block = handler[handler.index("} finally {"):]
    assert "flowYearInFlight = false" in finally_block
    assert "flowYearButton.textContent = FLOW_DATE_BUTTON_TEXT" in finally_block
    assert "updateFlowYearButton()" in finally_block
    for expected in (
        "計算逾時，請重試。", "網路連線失敗，請重試。", "伺服器回應格式錯誤，請重試。",
    ):
        assert expected in javascript


def test_flow_date_fetch_timeout_is_fifteen_seconds_and_uses_abort_controller() -> None:
    javascript = client.get("/static/ziwei.js").text
    helper = javascript[
        javascript.index("async function fetchFlowQuery"):
        javascript.index("function clearError")
    ]
    assert "const FLOW_DATE_TIMEOUT_MS = 15_000" in javascript
    assert "new AbortController()" in helper
    assert "setTimeout(() => controller.abort(), timeoutMs)" in helper
    assert "signal: controller.signal" in helper
    assert "clearTimeout(timeoutId)" in helper


def test_flow_date_ui_runtime_restores_controls_for_every_outcome_and_allows_retry() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is unavailable for the frontend Flow-Date runtime test")
    javascript = client.get("/static/ziwei.js").text
    validator = javascript[
        javascript.index("function validateFlowQuery"):
        javascript.index("function flowDateUiError")
    ]
    ui_error = javascript[
        javascript.index("function flowDateUiError"):
        javascript.index("async function fetchFlowQuery")
    ]
    error_messages = javascript[
        javascript.index("function flowYearErrorMessage"):
        javascript.index("function interpretationErrorMessage")
    ]
    handler = javascript[
        javascript.index("async function calculateFlowQueryFromInputs"):
        javascript.index('flowYearButton.addEventListener("click"')
    ]
    script = f"""
const FLOW_DATE_BUTTON_TEXT = "計算流年／流月／流日";
let currentBirthInput = {{ name: "Case A" }};
let flowYearInFlight = false;
let flowYearGeneration = 0;
let flowYearButton = {{ disabled: false, textContent: FLOW_DATE_BUTTON_TEXT }};
let flowYearStatus = {{ hidden: true, textContent: "" }};
let flowYearError = {{ hidden: true, textContent: "" }};
let rawTarget;
let mode;
let fetchCalls = 0;
let renderCalls = 0;
function collectFlowQuery() {{ return rawTarget; }}
function clearFlowYear() {{
  flowYearStatus.hidden = true;
  flowYearStatus.textContent = "";
  flowYearError.hidden = true;
  flowYearError.textContent = "";
}}
function updateFlowYearButton() {{ flowYearButton.disabled = flowYearInFlight || !currentBirthInput; }}
function renderFlowQuery() {{ renderCalls += 1; }}
{validator}
{ui_error}
{error_messages}
async function fetchFlowQuery() {{
  fetchCalls += 1;
  if (mode === "network") throw new TypeError("unsafe network detail");
  if (mode === "timeout") {{
    const error = new Error("aborted");
    error.name = "AbortError";
    throw error;
  }}
  if (mode === "malformed") return {{ ok: true, status: 200, json: async () => {{ throw new Error("bad json"); }} }};
  if (mode === "422") return {{ ok: false, status: 422, json: async () => ({{ detail: {{ code: "INVALID_FLOW_QUERY", message: "target query date cannot be earlier than the normalized birth date" }} }}) }};
  if (mode === "500") return {{ ok: false, status: 500, json: async () => ({{}}) }};
  return {{ ok: true, status: 200, json: async () => ({{ ok: true }}) }};
}}
{handler}
const valid = {{ mode: "solar", year: "2029", month: "2", day: "13" }};
const missing = {{ mode: "solar", year: "2026", month: "", day: "" }};
function reset() {{
  flowYearInFlight = false;
  flowYearButton.disabled = false;
  flowYearButton.textContent = FLOW_DATE_BUTTON_TEXT;
  flowYearStatus.hidden = true;
  flowYearStatus.textContent = "";
  flowYearError.hidden = true;
  flowYearError.textContent = "";
  fetchCalls = 0;
  renderCalls = 0;
}}
function snapshot() {{
  return {{
    loading: flowYearInFlight,
    disabled: flowYearButton.disabled,
    buttonText: flowYearButton.textContent,
    statusHidden: flowYearStatus.hidden,
    error: flowYearError.hidden ? "" : flowYearError.textContent,
    fetchCalls,
    renderCalls
  }};
}}
(async () => {{
  const results = {{}};
  reset(); rawTarget = missing; mode = "success";
  await calculateFlowQueryFromInputs(); results.missing = snapshot();
  for (const scenario of ["success", "422", "500", "network", "timeout", "malformed"]) {{
    reset(); rawTarget = valid; mode = scenario;
    await calculateFlowQueryFromInputs(); results[scenario] = snapshot();
  }}
  reset(); rawTarget = valid; mode = "success"; flowYearInFlight = true;
  await calculateFlowQueryFromInputs(); results.duplicate = snapshot();
  reset(); rawTarget = valid; mode = "network";
  await calculateFlowQueryFromInputs();
  mode = "success";
  await calculateFlowQueryFromInputs(); results.retry = snapshot();
  process.stdout.write(JSON.stringify(results));
}})();
"""
    process = subprocess.run(
        [node, "-e", script], check=False, capture_output=True, text=True, encoding="utf-8",
        timeout=5,
    )
    assert process.returncode == 0, process.stderr
    results = json.loads(process.stdout)

    assert results["missing"] == {
        "loading": False,
        "disabled": False,
        "buttonText": "計算流年／流月／流日",
        "statusHidden": True,
        "error": "國曆查詢請完整輸入年、月、日。",
        "fetchCalls": 0,
        "renderCalls": 0,
    }
    assert results["success"]["renderCalls"] == 1
    assert results["success"]["error"] == ""
    expected_errors = {
        "422": "運限查詢日期不可早於出生日期。",
        "500": "運限計算失敗，請稍後再試。",
        "network": "網路連線失敗，請重試。",
        "timeout": "計算逾時，請重試。",
        "malformed": "伺服器回應格式錯誤，請重試。",
    }
    for scenario, message in expected_errors.items():
        assert results[scenario]["error"] == message
        assert results[scenario]["renderCalls"] == 0
    for scenario in ("success", *expected_errors):
        assert results[scenario]["loading"] is False
        assert results[scenario]["disabled"] is False
        assert results[scenario]["buttonText"] == "計算流年／流月／流日"
        assert results[scenario]["statusHidden"] is True
        assert results[scenario]["fetchCalls"] == 1
    assert results["duplicate"]["fetchCalls"] == 0
    assert results["duplicate"]["renderCalls"] == 0
    assert results["retry"]["loading"] is False
    assert results["retry"]["disabled"] is False
    assert results["retry"]["fetchCalls"] == 2
    assert results["retry"]["renderCalls"] == 1
