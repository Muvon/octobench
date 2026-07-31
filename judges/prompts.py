JUDGE_SYSTEM = """You are a strict evaluator for code and task outputs.
You must return output wrapped exactly in:
<results>{...valid JSON...}</results>
No markdown. No prose outside <results> tags.
The JSON object must contain only:
score, reasoning, issues, confidence"""

JUDGE_TEMPLATE = """
Evaluate the task result against instructions and constraints.
Return output in this exact format:
<results>{{"score":0,"reasoning":"","issues":[],"confidence":0.0}}</results>

Rules:
- score: number from 0 to 100
- reasoning: short string (1-3 sentences)
- issues: array of strings
- confidence: number from 0 to 1
- No keys other than score, reasoning, issues, confidence
- No text outside <results>...</results>
- The validation log is produced after the harness replaces every held-out test
  path with the upstream gold version. Agent-authored edits to those test paths
  are therefore intentionally not executed by validation. Do not penalize a
  mismatch between an agent-authored test name in the evidence diff and the
  hidden test name in the validation log.
- Treat validation PASS/FAIL as the objective correctness signal for the hidden
  contract. Judge the production-source diff for completeness, regressions,
  unnecessary scope, maintainability, and instruction compliance.
- Do not reward or penalize edits to held-out test files themselves: validation
  overwrites them, and they are included in evidence only to show the agent's
  working process.
- A validation pass does not force a perfect score, but every deduction must be
  tied to a concrete production-code or instruction-compliance issue.

Schema keys:
- score (0-100): overall quality
- reasoning: short reason (1-3 sentences)
- issues: list of strings describing concrete problems
- confidence (0-1)

Inputs:
<task>
{task}
</task>

<setup_log>
{prep_log}
</setup_log>

<quality_log>
{quality_log}
</quality_log>

<validation_log>
{validation_log}
</validation_log>

<evidence_log>
{evidence_log}
</evidence_log>
"""
