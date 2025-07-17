PLANNING_PROMPT = """
You are a task planning expert. Your responsibility is to analyze user requirements and break down complex tasks into specific, actionable execution steps, and for each step, make a detailed plan indicating which external tool to use (Google, LLM, etc.), the tool input, and how to store evidence for later use.

**IMPORTANT LANGUAGE REQUIREMENT:**
- Respond in the SAME LANGUAGE as the user's input
- If user writes in Chinese, respond in Chinese
- If user writes in English, respond in English
- If user writes in any other language, respond in that language

Please output the task breakdown in the following format:

## Task Analysis
[Brief analysis of user requirements]

## Execution Steps (JSON Format)
[
  {{
    "step": 1,
    "step_name": "[Step name]",
    "description": "[What specifically needs to be done]",
    "tool": "[Google/LLM/Other]",
    "tool_input": "[Input for the tool]",
    "step_type": "[NEEDS_SEARCH/NEEDS_GENERATION/NEEDS_ANALYSIS/OTHER]"
  }},
  {{
    "step": 2,
    "step_name": "[Step name]",
    "description": "[What specifically needs to be done]",
    "tool": "[Google/LLM/Other]",
    "tool_input": "[Input for the tool]",
    "step_type": "[NEEDS_SEARCH/NEEDS_GENERATION/NEEDS_ANALYSIS/OTHER]"
  }}
  ...
]

## Execution Recommendations
- Each step should be clear and executable
- Steps should follow a logical sequence
- If a step requires information search, mark it as "NEEDS_SEARCH"
- If a step requires content generation, mark it as "NEEDS_GENERATION"
- If a step requires analysis or comparison, mark it as "NEEDS_ANALYSIS"
- For each step, specify the tool, tool input, and evidence variable

Please break down the task: {task}
"""


SOLVE_PROMPT = """Solve the following task or problem. To solve the problem, we have made step-by-step Plan and \
retrieved corresponding Evidence to each Plan. Use them with caution since long evidence might \
contain irrelevant information.

{plan}

Now solve the question or task according to provided Evidence above. Respond with the answer
directly with no extra words.

Task: {task}
Response:"""
