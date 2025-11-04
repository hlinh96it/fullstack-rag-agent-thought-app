class RAGPromptBuilder:
    
    def __init__(self, default_experties: str = 'normal') -> None:
        """Builder class for creating RAG prompts

        Args:
            default_experties (str, optional): Normal or arXiv agent. Defaults to 'normal'.
        """
        self.system_prompt = self._load_system_prompt(default_experties)
        
    def _load_system_prompt(self, default_experties: str = 'normal') -> str:
        if default_experties == 'arxiv':
            return (
                "You are an AI assistant specialized in answering questions about "
                "academic papers from arXiv. Base your answer STRICTLY on the provided "
                "paper excerpts."
            ) 
        else:
            return (
                "You are helpful assistant. Provide concise and short answer with max response length to 100 words."
            )
        