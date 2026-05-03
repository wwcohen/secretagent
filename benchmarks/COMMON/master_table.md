# Master comparison — all classes × learners × all benchmarks

There is one version of the codedistill pipeline. Cells are
distinguished by **which class of distillation** and **which LLM
was the learner** (Opus 4.6 vs Gemini 3.1 Pro Preview).

Legend for table cells:
- **baseline_full**: fresh DS-V3.1 baseline (full-size val), no distillation
- **archived_workflow**: archived hand-written workflow run filtered to DS-V3*
- **v1_baseline / v1_ptool / v1_e2e**: legacy numbers from [v1 doc](code_distillation_results.md)
- **c1_v2**: legacy Class 1 (mini sizes); kept for traceability
- **c1_opus / c1_gemini**: Class 1 = ptool codedistill (replace each simulate ptool with Python). Suffix is the learner LLM.
- **c2_opus / c2_gemini**: Class 2 = distill workflow (rewrite the top-level workflow to call hand-written ptools). Suffix is the learner LLM.
- **c3_opus / c3_gemini**: Class 3 = distill workflow with **induced** ptools (same as Class 2 but the ptool toolbox comes from the prof's LLM-discovered induced_ptools seed=42 modules). Suffix is the learner LLM.

Cells marked `—` had no run for that combination (no distill or 0 ENABLED ptools).

## Accuracy (%)

| sub_bench                |   baseline_full | archived_workflow   | v1_baseline   | v1_ptool   | v1_e2e   | c1_v2   | c1_opus   | c1_gemini   | c2_v2   |   c2_opus | c2_gemini   | c3_opus   | c3_gemini   |
|:-------------------------|----------------:|:--------------------|:--------------|:-----------|:---------|:--------|:----------|:------------|:--------|----------:|:------------|:----------|:------------|
| natplan_calendar         |              55 | 49                  | 54            | 84         | 90       | —       | 54        | —           | 93      |        87 | 59          | 64        | —           |
| natplan_meeting          |              29 | 30                  | 0             | —          | 0        | —       | 55        | —           | 0       |         3 | 29          | —         | 100         |
| natplan_trip             |              21 | 15                  | —             | —          | —        | 20      | 21        | 82          | 33      |        21 | 91          | —         | 70          |
| musr_murder              |              68 | 68                  | 70            | 70         | 0        | 70      | 68        | 61          | —       |        60 | 59          | 85        | 71          |
| musr_object              |              61 | 58                  | —             | —          | —        | —       | 61        | 55          | —       |        68 | 59          | —         | 52          |
| musr_team                |              53 | 61                  | —             | —          | —        | —       | 33        | 65          | —       |        60 | 56          | —         | 61          |
| bbh_sports_understanding |              99 | 97                  | 97            | 97         | 63       | 93      | 99        | 97          | 70      |        99 | 99          | —         | —           |
| bbh_penguins_in_a_table  |              72 | 63                  | 70            | 53         | 58       | 73      | 72        | 81          | 93      |        88 | 91          | —         | —           |
| bbh_geometric_shapes     |              37 | 42                  | 75            | 73         | —        | 47      | —         | —           | 87      |       100 | 35          | —         | —           |
| bbh_date_understanding   |              83 | 84                  | 39            | —          | 59       | —       | —         | —           | 63      |        88 | 84          | —         | —           |
| medcalc                  |              61 | 66                  | 38            | 44         | 42       | —       | —         | —           | —       |        62 | 61          | —         | —           |
| finqa                    |              67 | 66                  | 62            | 61         | 35       | 0       | 67        | 53          | —       |        67 | 67          | 25        | —           |
| rulearena_nba            |              74 | —                   | —             | —          | —        | —       | —         | —           | —       |       100 | —           | —         | 76          |
| rulearena_tax            |              78 | —                   | —             | —          | —        | —       | —         | —           | —       |       100 | —           | —         | —           |
| rulearena_airline        |              46 | —                   | 90            | —          | —        | —       | —         | —           | 100     |       100 | 100         | —         | —           |
| tabmwp                   |              36 | 95                  | —             | —          | —        | —       | 39        | 40          | —       |        45 | 51          | —         | —           |

## Cost (total USD over val set)

| sub_bench                | baseline_full   | archived_workflow   | v1_baseline   | v1_ptool   | v1_e2e   | c1_v2   | c1_opus   | c1_gemini   | c2_v2   | c2_opus   | c2_gemini   | c3_opus   | c3_gemini   |
|:-------------------------|:----------------|:--------------------|:--------------|:-----------|:---------|:--------|:----------|:------------|:--------|:----------|:------------|:----------|:------------|
| natplan_calendar         | $0.3            | $0.3                | $0.2          | $0.09      | $0       | —       | $0.3      | —           | —       | —         | $0.4        | —         | —           |
| natplan_meeting          | $0.5            | $0.5                | $0.2          | —          | $0       | —       | $0.2      | —           | —       | $0.01     | $0.5        | —         | —           |
| natplan_trip             | $0.4            | $0.4                | —             | —          | —        | $0.1    | $0.4      | $0.3        | $0.09   | $0.4      | —           | —         | $0.03       |
| musr_murder              | $0.6            | $0.5                | $0.8          | $0.8       | $0       | $0.2    | $0.6      | $0.6        | —       | $0.2      | $0.5        | $0.2      | $0.6        |
| musr_object              | $0.5            | $0.4                | —             | —          | —        | —       | $0.5      | $0.4        | —       | $0.5      | $0.6        | —         | $0.2        |
| musr_team                | $0.3            | $0.3                | —             | —          | —        | —       | $0.3      | $0.3        | —       | $0.4      | $0.3        | —         | $0.3        |
| bbh_sports_understanding | $0.1            | $0.1                | $0.1          | $0.09      | $0       | $0.04   | $0.1      | $0.06       | $0.04   | $0.1      | $0.1        | —         | —           |
| bbh_penguins_in_a_table  | $0.09           | $0.1                | $0.04         | $0.03      | $0       | $0.04   | $0.09     | $0.04       | $0      | $0.01     | $0          | —         | —           |
| bbh_geometric_shapes     | $0.4            | $0.6                | $1.6          | $0.9       | —        | $0.10   | —         | —           | —       | —         | $0.3        | —         | —           |
| bbh_date_understanding   | $0.07           | $0.3                | $0.3          | —          | $0       | —       | —         | —           | $0.02   | $0.09     | $0.2        | —         | —           |
| medcalc                  | $0.3            | $2.1                | $0.1          | $0.01      | $0       | —       | —         | —           | —       | $0.08     | $0.3        | —         | —           |
| finqa                    | $0.1            | $0.4                | $0.1          | $0.1       | $0       | —       | $0.1      | $0.1        | —       | $0.2      | $0.1        | $0.3      | —           |
| rulearena_nba            | $1.2            | —                   | —             | —          | —        | —       | —         | —           | —       | —         | —           | —         | $1.2        |
| rulearena_tax            | $0.9            | —                   | —             | —          | —        | —       | —         | —           | —       | —         | —           | —         | —           |
| rulearena_airline        | $0.9            | —                   | $0.5          | —          | —        | —       | —         | —           | —       | —         | —           | —         | —           |
| tabmwp                   | $0.1            | $0.2                | —             | —          | —        | —       | $0.09     | $0.10       | —       | $0.1      | $0.1        | —         | —           |

## N (val size)

| sub_bench                |   baseline_full | archived_workflow   | v1_baseline   | v1_ptool   | v1_e2e   | c1_v2   | c1_opus   | c1_gemini   | c2_v2   |   c2_opus | c2_gemini   | c3_opus   | c3_gemini   |
|:-------------------------|----------------:|:--------------------|:--------------|:-----------|:---------|:--------|:----------|:------------|:--------|----------:|:------------|:----------|:------------|
| natplan_calendar         |             100 | 100                 | —             | —          | —        | —       | 100       | —           | 30      |       100 | 100         | 100       | —           |
| natplan_meeting          |             100 | 100                 | —             | —          | —        | —       | 100       | —           | 30      |       100 | 100         | —         | 100         |
| natplan_trip             |             100 | 100                 | —             | —          | —        | 30      | 100       | 100         | 30      |       100 | 100         | —         | 100         |
| musr_murder              |              75 | 100                 | —             | —          | —        | 30      | 75        | 75          | —       |        75 | 75          | 20        | 75          |
| musr_object              |              75 | 106                 | —             | —          | —        | —       | 75        | 75          | —       |        75 | 75          | —         | 75          |
| musr_team                |              75 | 100                 | —             | —          | —        | —       | 75        | 75          | —       |        75 | 75          | —         | 75          |
| bbh_sports_understanding |              75 | 75                  | —             | —          | —        | 30      | 75        | 75          | 30      |        75 | 75          | —         | —           |
| bbh_penguins_in_a_table  |              43 | 60                  | —             | —          | —        | 30      | 43        | 43          | 30      |        43 | 43          | —         | —           |
| bbh_geometric_shapes     |              75 | 100                 | —             | —          | —        | 30      | —         | —           | 30      |        75 | 75          | —         | —           |
| bbh_date_understanding   |              75 | 100                 | —             | —          | —        | —       | —         | —           | 30      |        75 | 75          | —         | —           |
| medcalc                  |             100 | 1100                | —             | —          | —        | —       | —         | —           | —       |       100 | 100         | —         | —           |
| finqa                    |             100 | 300                 | —             | —          | —        | 100     | 100       | 100         | —       |       100 | 100         | 100       | —           |
| rulearena_nba            |              42 | —                   | —             | —          | —        | —       | —         | —           | —       |        42 | —           | —         | 42          |
| rulearena_tax            |              50 | —                   | —             | —          | —        | —       | —         | —           | —       |        50 | —           | —         | —           |
| rulearena_airline        |              50 | —                   | —             | —          | —        | —       | —         | —           | 30      |        50 | 50          | —         | —           |
| tabmwp                   |             100 | 100                 | —             | —          | —        | —       | 100       | 100         | —       |       100 | 100         | —         | —           |