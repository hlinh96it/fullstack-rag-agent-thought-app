import { apiDoc } from "@/lib/axios";

export const docApi = {
	/**
	 * Get all documents for a user (excludes doc_content for faster loading)
	 * @param {string} userId - The user ID
	 * @returns {Promise} Array of documents with metadata only
	 */
	getAllDocs: async (userId) => {
		return await apiDoc.get(`/${userId}`);
	},

	/**
	 * Get full document details including doc_content
	 * @param {string} userId - The user ID
	 * @param {string} docId - The document ID
	 * @returns {Promise} Complete document with full parsed content
	 */
	getDocumentDetail: async (userId, docId) => {
		return await apiDoc.get(`/${userId}/${docId}`);
	},

	addDoc: async (userId, docs) => {
		return await apiDoc.post(`/${userId}`, docs);
	},

	deleteDoc: async (userId, s3_path) => {
		return await apiDoc.delete(`/${userId}`, {
			data: { s3_path },
		});
	},

	/**
	 * Upload a file to S3, parse it with Docling, and save to MongoDB (parallel processing)
	 * @param {string} userId - The user ID
	 * @param {File} file - The PDF file to upload
	 * @returns {Promise} Response with document data and parsed sections count
	 */
	uploadAndParse: async (userId, file) => {
		const formData = new FormData();
		formData.append("file", file);

		return await apiDoc.post(`/upload/${userId}`, formData, {
			headers: {
				"Content-Type": "multipart/form-data",
			},
		});
	},

	/**
	 * Parse a document with Docling only (no upload)
	 * @param {File} file - The PDF file to parse
	 * @returns {Promise} Parsed document data
	 */
	parseOnly: async (file) => {
		const formData = new FormData();
		formData.append("file", file);

		return await apiDoc.post("/parse", formData, {
			headers: {
				"Content-Type": "multipart/form-data",
			},
		});
	},
};
