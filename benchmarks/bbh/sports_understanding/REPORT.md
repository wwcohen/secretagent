# Sports Understanding Benchmark Report

## Dataset

Sports Understanding: 250 problems judging sentence plausibility from
BIG-Bench Hard. All answers are True/False.

## Experiments

  ┌───────────────────────┬───────────┬──────────┬────────────────────────────────────────────────┐
  │        Config         │ LLM calls │  PTools  │                  Description                   │
  ├───────────────────────┼───────────┼──────────┼────────────────────────────────────────────────┤
  │ unstructured_baseline │ 2         │ none     │ 1 LLM call to convert answer to bool           │
  ├───────────────────────┼───────────┼──────────┼────────────────────────────────────────────────┤
  │ structured_baseline   │ 1         │ none     │                                                │
  ├───────────────────────┼───────────┼──────────┼────────────────────────────────────────────────┤
  │ react                 │ variable  │ simulate │ uses Pydantic react agent in simulate_pydantic │
  ├───────────────────────┼───────────┼──────────┼────────────────────────────────────────────────┤
  │ pot                   │ variable  │ simulate │                                                │
  ├───────────────────────┼───────────┼──────────┼────────────────────────────────────────────────┤
  │ workflow              │ 4-6       │ simulate │ hand-coded workflow from PTP paper             │
  └───────────────────────┴───────────┴──────────┴────────────────────────────────────────────────┘

## Results (validation, n=75)

  ┌────────────────────────┬──────────────┬─────────────┬───────────┬──────────┐                                                              
  │          path          │ correct mean │ correct sem │ cost mean │ cost sem │                                                            
  ├────────────────────────┼──────────────┼─────────────┼───────────┼──────────┤                                                              
  │ workflow               │ 0.986667     │ 0.013333    │ 0.001401  │ 0.000069 │
  ├────────────────────────┼──────────────┼─────────────┼───────────┼──────────┤                                                              
  │ unstructured baseline  │ 0.893333     │ 0.035884    │ 0.000325  │ 0.000015 │
  ├────────────────────────┼──────────────┼─────────────┼───────────┼──────────┤                                                              
  │ structured baseline    │ 0.760000     │ 0.049647    │ 0.000158  │ 0.000004 │                                                            
  ├────────────────────────┼──────────────┼─────────────┼───────────┼──────────┤                                                              
  │ react                  │ 0.760000     │ 0.049647    │ 0.003080  │ 0.000298 │
  ├────────────────────────┼──────────────┼─────────────┼───────────┼──────────┤                                                              
  │ pot                    │ 0.720000     │ 0.052195    │ 0.002468  │ 0.000126 │                                                            
  └────────────────────────┴──────────────┴─────────────┴───────────┴──────────┘       
  
## Analysis

Based on paired tests from
```
uv run python -m secretagent.cli.results pair --metric correct --metric cost  results/*
```

* Workflow is significantly more accurate than any other config
* Workflow costs more than the baselines but much less than ReAct or PoT (about 1/2 the cost of ReAct)
* The unstructured baseline is significantly more accurate than the structured baseline, but 
also more expensive (it has a second LLM call as implemented).
* ReAct and PoT are not significantly different in accuracy, but ReAct is significantly slower. 
