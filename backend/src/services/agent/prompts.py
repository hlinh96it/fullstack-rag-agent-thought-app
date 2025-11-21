class AgentPrompt:
    def __init__(self):
        self.grade_prompt = self.get_grade_prompt()
        self.rewrite_prompt = self.get_rewrite_prompt()

    def get_grade_prompt(self):
        return (
            "You are a grader assessing relevance of retrieved documents to a user question. \n"
            "Here is the retrieved content: \n\n {context} \n\n"
            "Here is the user question: {question} \n\n"
            "Grade as 'yes' if ANY of the following are true:\n"
            "- The content contains keywords related to the question\n"
            "- The content discusses topics related to the question's domain\n"
            "- The content provides context that could help answer the question\n"
            "- The content is from a similar subject area as the question\n\n"
            "Only grade as 'no' if the content is completely unrelated or off-topic.\n"
            "Be lenient - partial relevance is acceptable.\n"
            "Respond with 'yes' or 'no'."
        )

    def get_rewrite_prompt(self):
        return (
            "Analyze the following question and rephrase it to make it clearer and more specific "
            "for document retrieval, while maintaining the core intent.\n\n"
            "Original question: {question}\n\n"
            "Guidelines for rewriting:\n"
            "- Keep the main topic and intent unchanged\n"
            "- Add synonyms or related terms that might appear in documents\n"
            "- Make it more general if it's too specific, or add context if it's too vague\n"
            "- Use common terminology that would appear in formal documents\n"
            "- Keep it concise (1-2 sentences maximum)\n\n"
            "Rewritten question:"
        )
