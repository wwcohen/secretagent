# Datasets

This repository evaluates against publicly available benchmarks. Each
benchmark is owned by its upstream authors; only cached or downloadable
copies live in `benchmarks/<name>/data/`.

| Benchmark | Tasks used | License | Citation | In this repo |
|---|---|---|---|---|
| **BBH** (BIG-Bench Hard) | `sports_understanding`, `geometric_shapes`, `penguins_in_a_table`, `date_understanding` | MIT | Suzgun et al., 2022 — *Challenging BIG-Bench Tasks and Whether Chain-of-Thought Can Solve Them*, [arXiv:2210.09261](https://arxiv.org/abs/2210.09261) | Shipped under `benchmarks/bbh/<task>/data/` |
| **MuSR** | `murder_mysteries`, `object_placements`, `team_allocation` | CC BY 4.0 | Sprague et al., 2024 — *MuSR: Testing the Limits of Chain-of-thought with Multistep Soft Reasoning*, ICLR 2024, [arXiv:2310.16049](https://arxiv.org/abs/2310.16049) | Shipped under `benchmarks/musr/data/` (re-downloadable via `download.py`) |
| **NaturalPlan** | `calendar_scheduling`, `meeting_planning`, `trip_planning` | Apache 2.0 (code) and CC BY 4.0 (data) | Zheng et al., 2024 — *NATURAL PLAN: Benchmarking LLMs on Natural Language Planning*, [arXiv:2406.04520](https://arxiv.org/abs/2406.04520) | Shipped under `benchmarks/natural_plan/data/` |
| **MedCalc-Bench** | calculator-typed clinical questions (`physical`, `lab test`, `dosage`, `risk`, `diagnosis`, `severity`) | CC BY-SA 4.0 | Khandekar et al., 2024 — *MedCalc-Bench: Evaluating Large Language Models for Medical Calculations*, NeurIPS 2024 Datasets & Benchmarks, [arXiv:2406.12036](https://arxiv.org/abs/2406.12036) | Shipped under `benchmarks/medcalc/data/` |
| **TabMWP** | tabular math word problems | Code: MIT. Dataset: CC BY-NC-SA 4.0 | Lu et al., 2023 — *Dynamic Prompt Learning via Policy Gradient for Semi-structured Mathematical Reasoning*, ICLR 2023, [arXiv:2209.14610](https://arxiv.org/abs/2209.14610) | Fetched via `benchmarks/tabmwp/data/download.py` |
| **FinQA** | numerical reasoning over financial reports | MIT | Chen et al., 2021 — *FinQA: A Dataset of Numerical Reasoning over Financial Data*, EMNLP 2021, [arXiv:2109.00122](https://arxiv.org/abs/2109.00122) | Shipped under `benchmarks/finqa/data/` (re-downloadable via `download.py`) |
| **RuleArena** | `airline`, `nba`, `tax` | CC BY 4.0 | Zhou et al., 2025 — *RuleArena: A Benchmark for Rule-Guided Reasoning with LLMs in Real-World Scenarios*, ACL 2025, [arXiv:2412.08972](https://arxiv.org/abs/2412.08972) | Shipped under `benchmarks/rulearena/data/` |
| **MedAgentBench** | EHR-style medical agent tasks | MIT | Jiang et al., 2025 — *MedAgentBench: A Virtual EHR Environment to Benchmark Medical LLM Agents*, NEJM AI | Shipped under `benchmarks/medagentbench/data/` |
| **DesignBench** | UI reconstruction (optional) | per upstream | n/a | Not shipped; see `benchmarks/designbench/README.md` |

All code in this repository is released under the Apache License 2.0;
see [LICENSE](LICENSE).
