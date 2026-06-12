# MedCalc-Bench data — attribution

This benchmark uses **MedCalc-Bench v1.2**, fetched at snapshot time from
the Hugging Face Hub: <https://huggingface.co/datasets/ncbi/MedCalc-Bench-v1.2>

The dataset files (`data/train.json`, `data/test.json`) are **not committed** to
this repo — they total ~51MB. Regenerate them locally with:

```
make data            # or: uv run python expt.py snapshot-data
```

## License

MedCalc-Bench is released under **CC BY-SA 4.0**
(<https://creativecommons.org/licenses/by-sa/4.0/>). Per the dataset card, any
redistribution must be under the same license and with attribution; the local
snapshot produced here inherits CC BY-SA 4.0. Use versions v1.0–v1.2 for
reproducibility and state the version.

## Citation

> Khandekar, N., et al. *MedCalc-Bench: Evaluating Large Language Models for
> Medical Calculations.* NeurIPS 2024 Datasets and Benchmarks.

See the dataset card for the full citation and source-note licenses
(MedCalc-Bench incorporates notes from PMC-Patients / Open-Patients, also
CC BY-SA 4.0).