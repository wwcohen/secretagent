# TabMWP Data Provenance

## Description

TabMWP is a dataset of 38,431 grade-school math word problems that require reasoning over tabular data. Each problem pairs a natural-language question with a table (provided as both text and a pandas-ready dict), and asks for either a free-text numeric answer or a multiple-choice selection. Problems span grades 1–8 and cover operations like lookup, sum, average, comparison, and multi-step arithmetic.

## Relevance to Project

TabMWP is a good testbed for secretagent because the table-plus-question format naturally decomposes into tool-like steps (parse table, identify operation, extract values, compute, format answer), letting us compare zero-shot, workflow, program-of-thought, and orchestrated agent strategies on structured reasoning.

## Source

**Dataset:** TabMWP (Tabular Math Word Problems)
**Paper:** Lu et al., "Dynamic Prompt Learning via Policy Gradient for Semi-structured Mathematical Reasoning," ICLR 2023.
**arXiv:** https://arxiv.org/abs/2209.14610
**Repository:** https://github.com/lupantech/PromptPG
**License:** CC BY-NC-SA 4.0 (Attribution-NonCommercial-ShareAlike)

## Download

Data was downloaded from the PromptPG GitHub repository using `download.py` in this directory.

```bash
uv run benchmarks/tabmwp/data/download.py
```

## Files

| File | Description | Examples |
|------|-------------|---------|
| `problems_train.json` | Training split | 23,059 |
| `problems_dev.json` | Validation split | 7,686 |
| `problems_test.json` | Test split | 7,686 |
| `problems_dev1k.json` | 1K dev subset | 1,000 |
| `problems_test1k.json` | 1K test subset | 1,000 |
| `splits.json` | Split assignments | — |

## Format

Each JSON file is a dict keyed by string example IDs. Each example contains:
- `question`: the math word problem (text)
- `table`: pipe-delimited table (text)
- `table_for_pd`: dict ready for `pandas.DataFrame()`
- `choices`: list of options (multi-choice) or null (free-text)
- `answer`: gold answer (string)
- `solution`: step-by-step reasoning trace (text)
- `ques_type`: "free_text" or "multi_choice"
- `ans_type`: "integer_number", "decimal_number", "extractive_text", "boolean_text", "other_text"
- `grade`: integer 1-8
- `table_title`, `row_num`, `column_num`, `unit`, `split`

## Example

Raw data format (each example is keyed by a string ID):

```json
{
  "16": {
    "question": "Some friends discussed the sizes of their coin collections. What is the mean of the numbers?",
    "choices": null,
    "answer": "84",
    "unit": null,
    "table_title": "Coin collections",
    "table": "Name | Number of coins\nBraden | 76\nCamilla | 94\n...",
    "table_for_pd": {"Name": ["Braden", "Camilla", "..."], "Number of coins": ["76", "94", "..."]},
    "row_num": 9,
    "column_num": 2,
    "solution": "Read the numbers from the table.\n76, 94, ...\n672 ÷ 8 = 84\nThe mean is 84.",
    "ques_type": "free_text",
    "ans_type": "integer_number",
    "grade": 5,
    "split": "test"
  }
}
```