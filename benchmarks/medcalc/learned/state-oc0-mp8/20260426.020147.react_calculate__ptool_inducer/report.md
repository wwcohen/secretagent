# PtoolInducer report — calculate_medical_value

- Trace mode: `react`
- Only correct: False
- Model: `gemini/gemini-3.1-flash-lite-preview`
- Thoughts: 93, labeled: 93
- Unique categories: 5
- Synthesized ptools: 5

## Synthesized ptools

### 1. PerformMedicalCalculation
- Source category: **PERFORM MATHEMATICAL CALCULATION** (59 occurrences)
- short_desc: Extracts clinical variables from a patient note and computes specific medical scores or formulas.

### 2. EvaluateClinicalScoreCriteria
- Source category: **EVALUATE CLINICAL SCORE CRITERIA** (20 occurrences)
- short_desc: Systematically extracts patient data and maps it against clinical score criteria to compute a total score.

### 3. ManualClinicalComputation
- Source category: **MANUAL COMPUTATION AFTER TOOL FAILURE** (6 occurrences)
- short_desc: Performs manual medical calculations when automated tools fail or return ambiguous results.

### 4. AssessClinicalDataCompleteness
- Source category: **IDENTIFY MISSING CLINICAL INFORMATION** (4 occurrences)
- short_desc: Evaluates whether necessary clinical variables are present in the patient note to perform a specific medical calculation.

### 5. ExtractAndNormalizeClinicalData
- Source category: **EXTRACT AND CONVERT CLINICAL DATA** (4 occurrences)
- short_desc: Extracts clinical values from medical notes and normalizes them into standard units for medical calculations.
