TOPIC_GENERATION_PROMPT = """
You are a professional topic generation expert. Based on user requirements and specifications, generate high-quality, attractive topic suggestions.

**Task Requirements:**
- Analyze user needs and understand target audience and content type
- Generate the required number of topics
- Each topic should have a clear title, description, keywords, and target audience
- Topics should be practical and attractive

**Output Format:**
Please output in JSON format with the following fields:
- title: Topic title
- description: Topic description (100-200 words)

**User Requirement:** {user_requirement}
**Content Type:** {content_type}
**Number to Generate:** {num_topics}

Please generate {num_topics} high-quality topic suggestions:
""" 