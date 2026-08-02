import json
from pathlib import Path

from audit.utils import pydantic_json_default

DEFAULT_OUTPUT_DIR = Path(__file__).parent / "output"

# Pipeline order for the written report (not parallel completion order).
REPORT_SECTIONS: tuple[tuple[str, str], ...] = (
    ("claim_extractor", "claims"),
    ("rhetorical_auditor", "rhetorical_audit"),
    ("fact_checker", "fact_check"),
    ("judger", "judgment"),
    ("analyzer", "analysis"),
    ("synthesizer", "article"),
)


def default_output_path(stem: str) -> Path:
    return DEFAULT_OUTPUT_DIR / f"{stem}_audit.txt"


def _section_text(text: object) -> str:
    if isinstance(text, str):
        value = text.strip()
    elif text is None:
        value = ""
    else:
        value = json.dumps(
            text, ensure_ascii=False, indent=2, default=pydantic_json_default
        )
    return value if value else "(empty response)"


def print_agent_response(agent: str, text: object) -> None:
    print(f"\n{'=' * 60}", flush=True)
    print(f"[{agent}]", flush=True)
    print("=" * 60, flush=True)
    print(_section_text(text), flush=True)


def format_audit_report(result: dict) -> str:
    lines = [
        f"[{agent}]\n{_section_text(result.get(field))}\n"
        for agent, field in REPORT_SECTIONS
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_audit_report(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_audit_report(result), encoding="utf-8")
