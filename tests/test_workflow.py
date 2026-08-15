import asyncio
import importlib.util
import unittest
from pathlib import Path

WORKFLOW_PATH = (
    Path(__file__).parents[1]
    / "src"
    / "copilot-workflow-hosted"
    / "workflow.py"
)
SPEC = importlib.util.spec_from_file_location("workflow_under_test", WORKFLOW_PATH)
workflow = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(workflow)


class WorkflowTests(unittest.TestCase):
    def test_runs_stages_in_order_with_last_agent_context(self):
        calls = []

        async def fake_stage(name, instructions, prompt):
            calls.append((name, instructions, prompt))
            return f"{name}-output"

        result = asyncio.run(
            workflow.run_slogan_workflow("electric SUV", fake_stage)
        )

        self.assertEqual(
            [call[0] for call in calls],
            ["writer", "legal_reviewer", "formatter"],
        )
        self.assertEqual(calls[0][2], "electric SUV")
        self.assertIn("writer-output", calls[1][2])
        self.assertNotIn("legal_reviewer-output", calls[1][2])
        self.assertIn("legal_reviewer-output", calls[2][2])
        self.assertNotIn("writer-output", calls[2][2])
        self.assertEqual(result.output, "formatter-output")


if __name__ == "__main__":
    unittest.main()
