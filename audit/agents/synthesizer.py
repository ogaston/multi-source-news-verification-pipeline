"""Synthesizer agent — rewrite a neutral, straight article from the judgment."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from audit.llm import invoke_llm
from audit.state import StoryAuditState
from common.config import get_final_article_max_chars

FINAL_ARTICLE_MAX_CHARS = get_final_article_max_chars()

SYSTEM_PROMPT = """\
You are Synthesizer. You rewrite the story from Judger's decision.

Your job:
- Write a new article in Spanish, in the style of a Dominican news outlet
  (e.g. El Nuevo Diario, Diario Libre).
- Stay on the SAME NEWS TOPIC as the original cluster (headline and lead must
  match that topic). If the sources are about denuncias de ataques racistas /
  identidad / nacionalidad, that must be the center of the rewrite—not a generic
  sports biography.
- Use a clear headline and body with short paragraphs, neutral tone, and
  standard journalistic structure (lead, context, attributed quotes).
- Write in third person; attribute reported statements to the outlet or speaker
  (Según…, Pie escribió…, en una publicación…).
- Use only narrative_to_keep; omit absolutely_false material.
- For not_verifiable items, either omit them or clearly mark uncertainty—
  never present them as independently confirmed fact.
- Do not invent biographical details, ages, quotes, or events absent from
  narrative_to_keep.
- No sensational headlines, loaded adjectives, or rhetorical devices called
  out by the auditor.
- Keep the entire article (headline + body) under {max_chars} characters.
  Prefer a slightly shorter complete article over exceeding the limit.
  Finish complete sentences and paragraphs; never end mid-word, mid-sentence,
  or mid-thought. Do not cut the text off.
- Do NOT start the body with a location or dateline (for example
  "Santo Domingo.—"). Place/dateline is prepended later by the pipeline.

Output the rewritten article only (headline + body), entirely in Spanish.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            (
                "Max length: {max_chars} characters. Stay under that limit with a "
                "complete article; do not truncate mid-sentence.\n\n"
                "Original story cluster (topic reference only; do not copy loaded framing):\n\n"
                "{story}\n\n"
                "Judgment (authoritative for what to keep/omit):\n\n{judgment}"
            ),
        ),
    ]
)


def run(state: StoryAuditState) -> dict:
    max_chars = FINAL_ARTICLE_MAX_CHARS
    content = (
        invoke_llm(
            PROMPT,
            {
                "story": state.get("story") or "",
                "judgment": state.get("judgment") or "",
                "max_chars": max_chars,
            },
        )
        or ""
    ).strip()
    return {"article": content}
