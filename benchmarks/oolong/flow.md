# Oolong Flow (Simple)

```mermaid
flowchart LR
    subgraph step1 [Step 1]
        direction TB
        A[Context Window + Question]
        B[infer_context_schema]
        C[Get regex + label_set]
        A --> B --> C
    end
    D[Human stuff (parse context with regex)]
    subgraph step2 [Step 2]
        direction TB
        E[classify_entry_batch]
        F[Get labeled entries]
        E --> F
    end

    G[Human stuff (drop instance; keep date/user/label)]

    subgraph step3 [Step 3]
        direction TB
        H[answer_from_cached_records]
        I[Final Answer]
        H --> I
    end
    C --> D --> E
    F --> G --> H
```

- Context + question in
- Infer schema
- Parse entries
- Batch classify
- Compress records
- Answer from cached records
- Final answer out
