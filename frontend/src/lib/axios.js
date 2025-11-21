import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Create base axios instance with common config
const createApiClient = (baseURL, customTimeout = 30000) => {
	const client = axios.create({
		baseURL,
		timeout: customTimeout,
		headers: {
			"Content-Type": "application/json",
		},
	});

	// Request interceptor
	client.interceptors.request.use(
		(config) => {
			// Add auth token if needed
			// const token = localStorage.getItem('token');
			// if (token) config.headers.Authorization = `Bearer ${token}`;
			return config;
		},
		(error) => Promise.reject(error)
	);

	// Response interceptor
	client.interceptors.response.use(
		(response) => response.data,
		(error) => {
			const message = error.response?.data?.detail || error.message;
			console.error("API Error:", message);
			return Promise.reject({ message, status: error.response?.status });
		}
	);

	return client;
};

export const apiUser = createApiClient(`${API_BASE_URL}/user`);
export const apiChat = createApiClient(`${API_BASE_URL}/chat`, 10000); // 10s for chat operations
export const apiAsk = createApiClient(`${API_BASE_URL}/ask`, 600000); // 60s for ask operations (agent may take longer with tools)
export const apiS3 = createApiClient(`${API_BASE_URL}/s3`, 10000); // 10s for S03 operations
export const apiDoc = createApiClient(`${API_BASE_URL}/doc`, 600000); // 600s for document operations
export const apiPostgres = createApiClient(`${API_BASE_URL}/postgres`, 600000); // 600s for postgres operations
