# PtoolInducer report — calculate_medical_value

- Trace mode: `react`
- Only correct: False
- Model: `gemini/gemini-3.1-flash-lite-preview`
- Thoughts: 101, labeled: 101
- Unique categories: 5
- Synthesized ptools: 4

## Synthesized ptools

### 1. CalculateClinicalScore
- Source category: **Perform clinical formula calculation** (39 occurrences)
- short_desc: Performs clinical formula and medical score calculations based on extracted patient data.

### 2. ComputeClinicalValue
- Source category: **Perform arithmetic and unit conversion** (26 occurrences)
- short_desc: Perform clinical arithmetic and unit conversions using patient data and established medical formulas.

### 3. ApplyClinicalScore
- Source category: **Apply clinical scoring criteria** (19 occurrences)
- short_desc: Evaluates a specific clinical scoring system by extracting parameters from a patient note and calculating the total score.

### 4. ExtractClinicalVariables
- Source category: **Extract clinical data from note** (16 occurrences)
- short_desc: Extracts patient data from the clinical note to map them against the specific criteria of a medical scoring system.
