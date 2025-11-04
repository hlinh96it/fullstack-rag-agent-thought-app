import { apiChat } from "@/lib/axios";

export const chatApi = {
	getAllChats: async (userId) => {
		return await apiChat.get(`/${userId}`);
	},

	createChat: async (userId, chatData) => {
		return await apiChat.post(`/${userId}`, chatData);
	},

	deleteChat: async (userId, chatId) => {
		return await apiChat.delete(`/${userId}/${chatId}`);
	},

	addMessage: async (userId, chatId, message) => {
		return await apiChat.post(`/${userId}/${chatId}`, message);
	},
};
