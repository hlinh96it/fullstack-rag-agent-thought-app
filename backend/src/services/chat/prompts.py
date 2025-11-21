class RAGPromptBuilder:

    def __init__(self, default_experties: str = "normal") -> None:
        """Builder class for creating RAG prompts

        Args:
            default_experties (str, optional): Normal or arXiv agent. Defaults to 'normal'.
        """
        self.system_prompt = self._load_system_prompt(default_experties)

    def _load_system_prompt(self, default_experties: str = "normal") -> str:
        if default_experties == "normal":
            return (
                "Call the model to generate a response based on the current state. "
                "Given the question, it will decide to retrieve using the retriever tool, or simply respond to the user."
            )
        else:
            return (
                "You are a helpful AI assistant with access to document retrieval tools. "
                "IMPORTANT: You MUST ALWAYS use the available retriever tools to search for information "
                "before answering any user question. This is mandatory - do not answer from general knowledge. "
                "Always call one of the retriever tools first to find relevant context. "
                "Provide concise, accurate answers based strictly on the retrieved context. "
                "If the retrieved information is not relevant, you will get another chance to search. "
                "Keep responses focused and under 150 words when possible."
            )
