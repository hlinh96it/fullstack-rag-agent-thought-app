import { apiS3 } from "@/lib/axios";

export const s3Api = {
	getAllFiles: async (userId) => {
		return await apiS3.get(`/${userId}`);
	},

	uploadFiles: async (userId, files) => {
		return await apiS3.post(`/upload/${userId}`, files, {
			headers: {
				"Content-Type": "multipart/form-data",
			},
		});
	},

	downloadFile: async (s3_path) => {
		const [user_id, fileName] = s3_path.split("/");
		return await apiS3.get(`/download/${user_id}/${fileName}`, {
			responseType: "blob",
		});
	},

	deleteFile: async (s3_path) => {
		const [user_id, fileName] = s3_path.split("/");
		return await apiS3.delete(`/delete/${user_id}/${fileName}`);
	},
};
