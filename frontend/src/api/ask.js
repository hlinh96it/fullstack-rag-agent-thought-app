import { apiAsk } from "@/lib/axios";

export const askApi = {
	askQuestion: async (prompt) => {
		return await apiAsk.post("", { prompt });
	},
};
