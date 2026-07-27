SOLVE_PROMPT = """
You are an expert in financial data extraction and numerical reasoning.
First, think step-by-step:
1. Analyze the question to understand what specific values are needed. If a specific financial metric (like CET1 ratio) is asked but not explicitly named, use the closest available components (e.g., Tier 1 Capital / Risk-Weighted Assets) to calculate it.
2. Extract the exact numbers from the provided context and tables. Pay close attention to whether a given number is the original amount or the new amount after an increase/decrease.
3. Perform the calculation step-by-step. DO NOT round any intermediate or final calculations. Keep all decimal places.
Finally, on a new line at the very end, output ONLY the final answer (a number or percentage) as requested by the question.
"""

REVIEW_PROMPT = """
You are an expert reviewer. You are given a financial reasoning problem and an initial solution.
Please review the initial solution for any errors in data extraction or calculation.
1. Verify that all required years and categories from the question are included. Ensure the correct base values are used for percentage changes (e.g., original amount vs new amount).
2. Verify the mathematical calculations. DO NOT round any numbers. Keep all decimal places.
Finally, on a new line at the very end, output ONLY the corrected final answer (a number or percentage) as requested by the question.
"""