import { apiUser } from "@/lib/axios";

export const userApi = {
	getAllUsers: async () => {
		return await apiUser.get("/");
	},

	createUser: async (userData) => {
		return await apiUser.post("/", userData);
	},

	updateUser: async (user_id, userData) => {
		return await apiUser.put(`/${user_id}`, userData)
	}
};
