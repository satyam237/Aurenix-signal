# Week 0 Baseline (T-02)

Manual baseline runs establish the **before** picture for The Nautikal GEO case study.

## Steps

1. Open [`../prompts/nautikal_prompts.json`](../prompts/nautikal_prompts.json)
2. For each of the 25 prompts, run the text manually on:
   - ChatGPT (chat.openai.com)
   - Gemini (gemini.google.com)
3. Record results in [`week0_baseline.csv`](week0_baseline.csv)

## CSV columns

| Column | Description |
|--------|-------------|
| `prompt_id` | Pre-filled (e.g. `hi-01`) |
| `engine` | Pre-filled (`chatgpt` or `gemini`) |
| `brand_mentioned` | `Y` or `N` — was The Nautikal / thenautikal.com mentioned? |
| `rank_position` | Position in list if mentioned (1 = first), blank if N |
| `response_snippet` | Short excerpt showing brand mention context |
| `screenshot_path` | Path to saved screenshot file |
| `run_date` | ISO date (e.g. `2026-06-18`) |
| `notes` | Optional observations |

## Regenerate template

```bash
python scripts/generate_baseline_template.py
```

This overwrites empty rows — back up filled data first if re-running.
