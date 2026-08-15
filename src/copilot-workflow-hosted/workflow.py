"""Framework-independent orchestration for the sequential agent workflow."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

StageRunner = Callable[[str, str, str], Awaitable[str]]


@dataclass(frozen=True)
class WorkflowResult:
    writer: str
    legal_reviewer: str
    formatter: str

    @property
    def output(self) -> str:
        return self.formatter


WRITER_INSTRUCTIONS = """
You are the writer stage in a sequential workflow.
Create five concise Korean slogan candidates for the supplied product topic.
Do not invent numbers, awards, guarantees, or unsupported comparisons.
Return only the candidates and a one-line rationale for each.
""".strip()

LEGAL_INSTRUCTIONS = """
You are the legal-review stage in a sequential workflow.
Review only the writer output supplied in the user prompt.
Remove or revise guarantees, absolute superiority claims, unverifiable facts,
and wording that could mislead a consumer. Preserve the creative intent.
Return the corrected candidates and briefly identify material corrections.
""".strip()

FORMATTER_INSTRUCTIONS = """
You are the formatter stage in a sequential workflow.
Use only the reviewed content supplied in the user prompt.
Produce polished Korean Markdown with a title, a numbered list of final slogans,
and a short section named '검토 메모'. Do not add new factual claims.
""".strip()


async def run_slogan_workflow(topic: str, run_stage: StageRunner) -> WorkflowResult:
    """Run writer, legal reviewer, and formatter with last-agent-only context."""
    writer = await run_stage("writer", WRITER_INSTRUCTIONS, topic)

    legal_reviewer = await run_stage(
        "legal_reviewer",
        LEGAL_INSTRUCTIONS,
        f"원래 주제: {topic}\n\nWriter 출력:\n{writer}",
    )

    formatter = await run_stage(
        "formatter",
        FORMATTER_INSTRUCTIONS,
        f"원래 주제: {topic}\n\nLegal reviewer 출력:\n{legal_reviewer}",
    )

    return WorkflowResult(
        writer=writer,
        legal_reviewer=legal_reviewer,
        formatter=formatter,
    )

