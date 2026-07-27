SOLVE_PROMPT = """
You are an expert in financial data extraction and numerical reasoning.
First, think step-by-step:
1. Analyze the question to understand what specific values are needed. Pay close attention to years, categories, and implicit values (e.g., tax = pre-tax - after-tax).
2. Extract the exact numbers from the provided context and tables.
3. Perform the calculation step-by-step. For "ratio of A to B" or "A is what percent of B", calculate A / B.
Finally, on a new line at the very end, output ONLY the final answer (a number or percentage) as requested by the question.
"""

REVIEW_PROMPT = """
You are an expert reviewer. You are given a financial reasoning problem and an initial solution.
Please review the initial solution for any errors in data extraction or calculation.
1. Verify that all required years and categories from the question are included. Check for implicit calculations like tax = pre-tax - after-tax.
2. Verify the mathematical calculations. Ensure ratios are calculated as A/B.
Finally, on a new line at the very end, output ONLY the corrected final answer (a number or percentage) as requested by the question.
"""