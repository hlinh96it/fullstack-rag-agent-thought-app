import { apiDoc } from "@/lib/axios";

export const docApi = {
	getAllDocs: async (userId) => {
		return await apiDoc.get(`/${userId}`);
	},

	addDoc: async (userId, docs) => {
		return await apiDoc.post(`/${userId}`, docs);
	},

	deleteDoc: async (userId, s3_path) => {
		return await apiDoc.delete(`/${userId}`, {
			data: { s3_path },
		});
	},
};
