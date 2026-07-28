## AFlow arm (executor gemini-2.5-flash-lite, optimizer gemini-3.1-pro-preview)
| bench   |   rounds |   cand_evals |   best_round |   best_val |   test |   test_n |   test_cost_per_case |   search_cost |   search_exec_cost |   search_opt_cost_est |   search_cost_incl_failed_attempts |
|:--------|---------:|-------------:|-------------:|-----------:|-------:|---------:|---------------------:|--------------:|-------------------:|----------------------:|-----------------------------------:|
| sports  |        9 |           27 |            1 |       0.76 |   0.59 |      100 |             0.000107 |        0.5861 |             0.4982 |                0.0879 |                             0.5861 |
| finqa   |       12 |           18 |            3 |       0.72 |   0.67 |      300 |             0.001055 |        5.9314 |             1.5461 |                4.3854 |                             9.4048 |

## Reference cells (same executor, secretagent harness)
| bench   | method       | split   |   n |   correct |   cost |
|:--------|:-------------|:--------|----:|----------:|-------:|
| sports  | workflow     | valid   |  50 |    0.94   | 0.0074 |
| sports  | react        | valid   |  50 |    0.86   | 0.0116 |
| sports  | structured   | valid   |  50 |    0.9    | 0.0014 |
| sports  | unstructured | valid   |  50 |    0.74   | 0.0018 |
| sports  | workflow     | test    | 100 |    0.81   | 0.0147 |
| sports  | react        | test    | 100 |    0.59   | 0.015  |
| sports  | structured   | test    | 100 |    0.85   | 0.0027 |
| sports  | unstructured | test    | 100 |    0.82   | 0.0036 |
| finqa   | workflow     | valid   |  50 |    0.84   | 0.0122 |
| finqa   | react        | valid   |  50 |    0.12   | 0.0048 |
| finqa   | structured   | valid   |  50 |    0.3    | 0.0071 |
| finqa   | workflow     | test    | 300 |    0.7567 | 0.0741 |
| finqa   | react        | test    | 300 |    0.07   | 0.0241 |
| finqa   | structured   | test    | 300 |    0.25   | 0.0426 |
| finqa   | zeroshot     | valid   |  50 |    0.54   | 0.006  |
| finqa   | zeroshot     | test    | 300 |    0.39   | 0.036  |

## AFlow candidate audit — every searched Sports round on held-out test
|   round |   val |   test |   cost_per_case |   calls_per_case |   out_tok_per_case |
|--------:|------:|-------:|----------------:|-----------------:|-------------------:|
|       1 |  0.76 |   0.75 |       3.2e-06   |             1    |                1   |
|       2 |  0.76 |   0.75 |       9.91e-05  |             4    |              181.3 |
|       3 |  0.44 |   0.5  |       0.000933  |             7    |             2177.7 |
|       4 |  0.76 |   0.78 |       0.0004215 |             2.18 |              847.3 |
|       5 |  0.74 |   0.78 |       0.0013462 |             7.47 |             2704.7 |
|       6 |  0.56 |   0.53 |       1e-05     |             2    |                2   |
|       7 |  0.76 |   0.75 |       0.0001139 |             6    |              201.2 |
|       8 |  0.76 |   0.77 |       0.0006836 |             3.12 |             1362.4 |
|       9 |  0.54 |   0.59 |       0.0001067 |             5    |              182.3 |
