SOLVE_PROMPT = """You are an expert in financial analysis and numerical reasoning.
Please read the provided financial report excerpt carefully and solve the question step-by-step.
1. Identify the specific numbers needed to answer the question from the text and tables. Pay attention to units (e.g., millions, thousands).
2. Perform the necessary mathematical calculations step-by-step.
3. Format the final answer exactly as requested. For rates or proportions, answer as a decimal (e.g., 0.06354) or a percent (e.g., 6.35%).

Provide your step-by-step reasoning, and then state the final answer on a new line starting with "Final Answer: ". Do not include any other text after the final answer."""