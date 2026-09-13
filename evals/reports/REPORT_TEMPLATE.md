# Moderation Evaluation Report Template

| Field | Value |
|---|---|
| Date | YYYY-MM-DD |
| Gateway version | 0.1.0 |
| Policy version | v1 |
| Prompt version | v1 |
| Model alias | moderation-fast |
| Effective model | gpt-oss:20b |
| Dataset | evals/samples/sample_eval.jsonl |
| Dataset version | v0 |

## Disclaimer

This gateway uses **general-purpose** Ollama models as classifiers.
`category_scores` are **heuristic risk estimates**, not calibrated probabilities.
Results are **not equivalent** to OpenAI `omni-moderation-latest`.
Do not ship to production without evaluation on your own languages and risk appetite.

## Overall metrics

| Metric | Value |
|---|---|
| Precision | |
| Recall | |
| F1 | |
| False positives | |
| False negatives | |

## By language

| Language | Precision | Recall | F1 |
|---|---|---|---|
| zh | | | |
| en | | | |
| mixed | | | |

## Latency

| Stat | ms |
|---|---|
| p50 | |
| p95 | |
| mean | |

## Threshold notes

Document any threshold changes in `configs/policy.yaml` and re-run `scripts/evaluate.py`.

## Decision

- [ ] Approved for pilot
- [ ] Needs threshold tuning
- [ ] Needs different model / policy
