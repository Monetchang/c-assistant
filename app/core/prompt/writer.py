OUTLINE_GENERATION_PROMPT = """
You are a professional article outline generation expert. Based on the given topic and requirements, create a clear, logical, and well-structured outline.

**Task Requirements:**
- Analyze the topic and determine the core viewpoints of the article
- Design a reasonable article structure
- Each section should have a clear title and description
- Ensure logical coherence between sections
- Consider target audience and content type

**Output Format:**
Please output in JSON format with the following fields:
- title: Article title
- introduction: Introduction section description
- sections: List of sections, each containing title and description
- conclusion: Conclusion section description

**Topic:** {topic}
**Content Type:** {content_type}
**Target Length:** {target_length}

Please generate a high-quality article outline:
"""

ARTICLE_WRITING_PROMPT = """
You are a professional article writing expert. Based on the provided outline and related information, create high-quality article content.

**Task Requirements:**
- Strictly follow the outline structure for writing
- Content should be rich, in-depth, and valuable
- Language should be clear, fluent, and readable
- Maintain professional writing style
- Ensure clear logic and well-defined viewpoints

**Writing Style:** {style}
**Outline:** {outline}
**Additional Information:** {additional_info}

Please create complete article content based on the above information. Output the article text directly without JSON format:
""" 