"""Offline migration gates; these do not claim Android-device runtime PASS."""

import json
import shutil
import subprocess
from pathlib import Path

from app.llm.interpreter import SYSTEM_PROMPT
from app.llm.major_luck_interpreter import MAJOR_LUCK_SYSTEM_PROMPT
from app.llm.flow_year_interpreter import FLOW_YEAR_SYSTEM_PROMPT
from app.llm.flow_period_interpreter import FLOW_MONTH_SYSTEM_PROMPT, FLOW_DAY_SYSTEM_PROMPT
from app.models.interpretation import InterpretationResult
from app.models.major_luck_interpretation import MajorLuckInterpretationResult
from app.models.flow_year_interpretation import FlowYearInterpretationResult
from app.models.flow_period_interpretation import FlowMonthInterpretationResult, FlowDayInterpretationResult

ROOT = Path(__file__).resolve().parents[1]


def test_android_system_prompts_and_schemas_match_accepted_python() -> None:
    source = (ROOT / "android/ziwei-core/src/main/java/com/tiger/ziwei/core/AcceptedAiContracts.kt").read_text(encoding="utf-8")
    prompts = dict(zip(("natal", "major_luck", "flow_year", "flow_month", "flow_day"),
                      (SYSTEM_PROMPT, MAJOR_LUCK_SYSTEM_PROMPT, FLOW_YEAR_SYSTEM_PROMPT, FLOW_MONTH_SYSTEM_PROMPT, FLOW_DAY_SYSTEM_PROMPT)))
    for scope, prompt in prompts.items():
        copied = source.split(f'"{scope}" to """', 1)[1].split('"""', 1)[0]
        assert copied == prompt
    raw_schema = source.split('val schemas = JsonParser.parseString("""', 1)[1].split('"""', 1)[0]
    schemas = json.loads(raw_schema.replace("${'$'}", "$"))
    models = (InterpretationResult, MajorLuckInterpretationResult, FlowYearInterpretationResult, FlowMonthInterpretationResult, FlowDayInterpretationResult)
    assert schemas == {scope: model.model_json_schema() for scope, model in zip(prompts, models)}
    assert "\ufffd" not in source


def test_standalone_ui_transport_and_offline_word_state_in_node() -> None:
    node = shutil.which("node")
    assert node, "Node required for the standalone transport gate"
    process = subprocess.run([node, "tests/verify_standalone_ui.cjs"], cwd=ROOT,
                             capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert process.returncode == 0, process.stderr
    receipt = json.loads(process.stdout)
    assert receipt["offlineWordEnabled"] is True
    assert receipt["birthMasked"] is True
    assert receipt["modelChangePreservesFacts"] is True
    assert receipt["unknownActionRejected"] is True
    assert receipt["blankKeyMessage"] == "請輸入 NVIDIA API KEY。"
    assert receipt["docxSaved"] is True
    assert receipt["unexpectedNetworkCalls"] == 0
