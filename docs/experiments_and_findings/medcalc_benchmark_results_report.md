# MedCalc Benchmark Results Report

Source result CSVs: the original five full-test experiments plus
`workflowv2_test_full`. Costs are recomputed from observed tokens with Together
DeepSeek-V3.1 prices: $0.60/M input tokens and $1.70/M output tokens.
`recorded_cost` is kept as a sanity check. `accuracy` is the CSV `correct`
field, which this evaluator writes from `is_within_tolerance`; therefore
`accuracy` and `within_tolerance` are identical here.

## Overall

| method | n | input_tokens | output_tokens | token_priced_cost | recorded_cost | cost_delta | total_latency_s | exact_match | within_tolerance | within_limits | accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unstructured | 1,100 | 2,214,840 | 586,514 | $2.3260 | $2.3260 | $0.0000 | 26,679.5 | 0.5045 | 0.7282 | 0.7282 | 0.7282 |
| Structured | 1,100 | 2,721,242 | 288,506 | $2.1232 | $2.1232 | $0.0000 | 12,706.6 | 0.3818 | 0.5127 | 0.5100 | 0.5127 |
| Workflow v1 | 1,100 | 2,797,605 | 229,593 | $2.0689 | $2.0689 | $0.0000 | 7,957.1 | 0.6218 | 0.6600 | 0.6582 | 0.6600 |
| ReAct | 1,100 | 18,625,654 | 1,279,773 | $13.3510 | $13.3510 | $0.0000 | 65,435.0 | 0.5409 | 0.6545 | 0.6536 | 0.6545 |
| PoT | 1,100 | 5,016,414 | 1,347,285 | $5.3002 | $5.3002 | $0.0000 | 45,562.6 | 0.5191 | 0.6009 | 0.6000 | 0.6009 |
| Workflow v2 | 1,100 | 3,332,333 | 273,533 | $2.4644 | $2.4644 | $0.0000 | 9,396.6 | 0.6518 | 0.6818 | 0.6809 | 0.6818 |

## Formulas vs Rules Split

Formulas = `physical`, `lab test`, `dosage`.
Rules = `diagnosis`, `risk`, `severity`.
Date calculators are retained in the full test-set table, but are excluded
from this formulas/rules split.

| method | partition | n | token_priced_cost | exact_match | within_tolerance | within_limits | accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Unstructured | Formulas | 660 | $1.2980 | 0.4864 | 0.8591 | 0.8591 | 0.8591 |
| Unstructured | Rules | 380 | $0.9066 | 0.6158 | 0.6158 | 0.6158 | 0.6158 |
| Structured | Formulas | 660 | $1.2360 | 0.3833 | 0.5970 | 0.5970 | 0.5970 |
| Structured | Rules | 380 | $0.7935 | 0.4395 | 0.4474 | 0.4395 | 0.4474 |
| Workflow v1 | Formulas | 660 | $0.9676 | 0.7530 | 0.8136 | 0.8136 | 0.8136 |
| Workflow v1 | Rules | 380 | $1.0378 | 0.4921 | 0.4974 | 0.4921 | 0.4974 |
| ReAct | Formulas | 660 | $7.9029 | 0.6318 | 0.8197 | 0.8197 | 0.8197 |
| ReAct | Rules | 380 | $4.8890 | 0.4684 | 0.4711 | 0.4684 | 0.4711 |
| PoT | Formulas | 660 | $3.0916 | 0.6167 | 0.7515 | 0.7515 | 0.7515 |
| PoT | Rules | 380 | $2.0567 | 0.4316 | 0.4342 | 0.4316 | 0.4342 |
| Workflow v2 | Formulas | 660 | $1.1393 | 0.7848 | 0.8333 | 0.8333 | 0.8333 |
| Workflow v2 | Rules | 380 | $1.2994 | 0.5026 | 0.5053 | 0.5026 | 0.5053 |

## Coarse Calculator Type Breakdown

| method | category | n | token_priced_cost | exact_match | within_tolerance | within_limits | accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Unstructured | physical | 240 | $0.3862 | 0.3708 | 0.9458 | 0.9458 | 0.9458 |
| Unstructured | lab test | 380 | $0.8266 | 0.5921 | 0.8553 | 0.8553 | 0.8553 |
| Unstructured | dosage | 40 | $0.0852 | 0.1750 | 0.3750 | 0.3750 | 0.3750 |
| Unstructured | date | 60 | $0.1214 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Unstructured | diagnosis | 60 | $0.1179 | 0.8000 | 0.8000 | 0.8000 | 0.8000 |
| Unstructured | risk | 240 | $0.5999 | 0.5833 | 0.5833 | 0.5833 | 0.5833 |
| Unstructured | severity | 80 | $0.1887 | 0.5750 | 0.5750 | 0.5750 | 0.5750 |
| Structured | physical | 240 | $0.3878 | 0.3167 | 0.6333 | 0.6333 | 0.6333 |
| Structured | lab test | 380 | $0.7802 | 0.4553 | 0.6158 | 0.6158 | 0.6158 |
| Structured | dosage | 40 | $0.0679 | 0.1000 | 0.2000 | 0.2000 | 0.2000 |
| Structured | date | 60 | $0.0937 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Structured | diagnosis | 60 | $0.1062 | 0.5667 | 0.5667 | 0.5667 | 0.5667 |
| Structured | risk | 240 | $0.5216 | 0.3833 | 0.3875 | 0.3833 | 0.3875 |
| Structured | severity | 80 | $0.1656 | 0.5125 | 0.5375 | 0.5125 | 0.5375 |
| Workflow v1 | physical | 240 | $0.2985 | 0.8542 | 0.9292 | 0.9292 | 0.9292 |
| Workflow v1 | lab test | 380 | $0.6248 | 0.7632 | 0.8079 | 0.8079 | 0.8079 |
| Workflow v1 | dosage | 40 | $0.0443 | 0.0500 | 0.1750 | 0.1750 | 0.1750 |
| Workflow v1 | date | 60 | $0.0635 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Workflow v1 | diagnosis | 60 | $0.1525 | 0.7000 | 0.7000 | 0.7000 | 0.7000 |
| Workflow v1 | risk | 240 | $0.6856 | 0.4083 | 0.4125 | 0.4083 | 0.4125 |
| Workflow v1 | severity | 80 | $0.1998 | 0.5875 | 0.6000 | 0.5875 | 0.6000 |
| ReAct | physical | 240 | $2.4118 | 0.6292 | 0.9542 | 0.9542 | 0.9542 |
| ReAct | lab test | 380 | $5.1686 | 0.6789 | 0.7789 | 0.7789 | 0.7789 |
| ReAct | dosage | 40 | $0.3225 | 0.2000 | 0.4000 | 0.4000 | 0.4000 |
| ReAct | date | 60 | $0.5591 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| ReAct | diagnosis | 60 | $0.6345 | 0.7167 | 0.7167 | 0.7167 | 0.7167 |
| ReAct | risk | 240 | $3.2288 | 0.4167 | 0.4208 | 0.4167 | 0.4208 |
| ReAct | severity | 80 | $1.0257 | 0.4375 | 0.4375 | 0.4375 | 0.4375 |
| PoT | physical | 240 | $0.8916 | 0.7333 | 0.8917 | 0.8917 | 0.8917 |
| PoT | lab test | 380 | $2.0878 | 0.6000 | 0.7211 | 0.7211 | 0.7211 |
| PoT | dosage | 40 | $0.1122 | 0.0750 | 0.2000 | 0.2000 | 0.2000 |
| PoT | date | 60 | $0.1519 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| PoT | diagnosis | 60 | $0.2615 | 0.6667 | 0.6667 | 0.6667 | 0.6667 |
| PoT | risk | 240 | $1.3524 | 0.3500 | 0.3500 | 0.3500 | 0.3500 |
| PoT | severity | 80 | $0.4429 | 0.5000 | 0.5125 | 0.5000 | 0.5125 |
| Workflow v2 | physical | 240 | $0.3293 | 0.9125 | 0.9625 | 0.9625 | 0.9625 |
| Workflow v2 | lab test | 380 | $0.7673 | 0.7816 | 0.8184 | 0.8184 | 0.8184 |
| Workflow v2 | dosage | 40 | $0.0427 | 0.0500 | 0.2000 | 0.2000 | 0.2000 |
| Workflow v2 | date | 60 | $0.0258 | 0.1333 | 0.1333 | 0.1333 | 0.1333 |
| Workflow v2 | diagnosis | 60 | $0.1787 | 0.6500 | 0.6500 | 0.6500 | 0.6500 |
| Workflow v2 | risk | 240 | $0.8760 | 0.4625 | 0.4667 | 0.4625 | 0.4667 |
| Workflow v2 | severity | 80 | $0.2447 | 0.5125 | 0.5125 | 0.5125 | 0.5125 |
