import { apiAsk } from "@/lib/axios";

export const askApi = {
	askQuestion: async (prompt, chatHistory = null) => {
		const payload = { prompt };
		if (chatHistory && chatHistory.length > 0) {
			payload.chat_history = chatHistory;
		}
		const response = await apiAsk.post("", payload);
		// The backend now returns { answer, retrieved_documents, processing_steps, search_count, rewrite_count }
		return response;
	},

	getAgentStatus: async () => {
		const response = await apiAsk.get("/status");
		return response.data;
	},
};
