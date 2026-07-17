# TOEFL 2026 LLM task grader

`app/toefl_2026_grader.py` implements the optional one-task LLM contract for
Write an Email and Academic Discussion. It returns an integer **0-5 task
score**. It does not estimate the final 1-6 Writing section band; that band
depends on all three task results, including Build a Sentence.

The deterministic offline scorer is the default and safety fallback. When a
user explicitly enables OpenAI, Claude, or Gemini and supplies a valid key,
`POST /api/evaluate` uses a response that passes this contract as the displayed
0-5 task score. Provider, parsing, schema, or semantic-validation failures fall
back to the offline score and expose `score_source="heuristic_fallback"` plus a
user-facing reason.

## Safety and validation

- The system prompt contains only trusted rubric and output instructions.
- `prompt_bullets` and `essay_text` are sent as untrusted JSON data, so an
  instruction written inside a student's response cannot replace the rubric.
- The application computes the word count and verifies the model's value.
- Pydantic strict mode rejects missing/extra fields and type coercion such as
  `"4"` in place of integer `4`.
- Code verifies the exact four dimension keys for the selected task, target
  range, template evidence, error excerpts, and the meaning-impeding error
  count. Required-point, tone, paragraph, and sentence-length observations do
  not create mechanical caps.
- Markdown-wrapped or prose-prefixed JSON is rejected. JSON parsing gets one
  retry, and a schema failure gets one corrective re-request.
- OpenAI uses the Responses API with strict `text.format` JSON Schema; Gemini
  uses `responseJsonSchema`; Claude uses strict JSON plus the same code-level
  validation.
- Word-count ranges are advisory. Extra length alone is not a deduction when
  the response remains relevant, purposeful, controlled, and nearly error-free.
- Conventional Email openings/closings and prompt-specific Academic Discussion
  framing are not automatically treated as template abuse.
- Mentioning another student is optional in Academic Discussion. The grader
  must not deduct solely because no classmate is named.

## Claude usage

With shadow Claude configuration loaded, call the dedicated method:

```python
from app.claude_provider import ClaudeScoringProvider
from app.shadow_config import load_shadow_config

grader = ClaudeScoringProvider(load_shadow_config())
result = grader.grade_task(
    task_type="email",
    prompt_bullets=[
        "Explain why you are writing.",
        "Describe the problem.",
        "Request a specific solution.",
    ],
    essay_text="Dear Professor, ...",
    feedback_language="ko",
)
print(result.model_dump_json())
```

The normal `ClaudeScoringProvider.run()` method remains the multi-stage shadow
pipeline with evidence-offset verification and an independent critic. Its task
dimension names and scoring instructions now use the same 2026 four-axis
rubric, while `grade_task()` is the exact single-call JSON contract.
