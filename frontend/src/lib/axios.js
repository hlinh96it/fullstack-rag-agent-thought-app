import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Create base axios instance with common config
const createApiClient = (baseURL) => {
	const client = axios.create({
		baseURL,
		timeout: 10000,
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
export const apiChat = createApiClient(`${API_BASE_URL}/chat`);
export const apiAsk = createApiClient(`${API_BASE_URL}/ask`);
export const apiS3 = createApiClient(`${API_BASE_URL}/s3`)
export const apiDoc = createApiClient(`${API_BASE_URL}/doc`)
