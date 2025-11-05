import { useState, useCallback, useEffect, useRef } from "react";
import { toast } from "sonner";
import { s3Api } from "@/api/s3";
import { docApi } from "@/api/doc";
import { useAppContext } from "@/context/AppContext";

export const useFileManagement = (userId) => {
	const { updateUserDocList } = useAppContext();
	const [files, setFiles] = useState([]);
	const [uploading, setUploading] = useState(false);
	const [uploadedFiles, setUploadedFiles] = useState([]);
	const [loading, setLoading] = useState(false);
	const pollingIntervalRef = useRef(null);

	// Upload progress tracking
	const [uploadProgress, setUploadProgress] = useState({
		current: 0,
		total: 0,
		stage: null, // 's3', 'mongodb', 'chunking', 'complete'
		percentage: 0,
		fileName: null,
	});

	// Utility: Sort files by uploaded_date desc
	const sortFilesByDate = useCallback((filesArray) => {
		return filesArray.sort(
			(a, b) => (b.uploaded_date || 0) - (a.uploaded_date || 0)
		);
	}, []);

	// Fetch uploaded files (with option for silent refresh)
	const fetchUploadedFiles = useCallback(
		async (silent = false) => {
			if (!silent) setLoading(true);
			try {
				const response = await docApi.getAllDocs(userId);
				const filesArray = Object.values(response);
				const sortedFiles = sortFilesByDate(filesArray);
				setUploadedFiles(sortedFiles);
				updateUserDocList(sortedFiles); // Update global user doc_list

				if (!silent) {
					toast.success(`Loaded ${sortedFiles.length} files`);
				}

				// Check if any files are still processing
				// Backend now checks MongoDB for chunk_data and updates status
				const hasProcessing = sortedFiles.some(
					(file) =>
						file.chunked === "processing" || file.chunked === false
				);

				return hasProcessing;
			} catch (error) {
				console.error("Error fetching files:", error);
				if (!silent && error.response?.status !== 500) {
					toast.error("Failed to fetch uploaded files");
				}
				return false;
			} finally {
				if (!silent) setLoading(false);
			}
		},
		[userId, sortFilesByDate, updateUserDocList]
	);

	// Start polling for chunking status
	const startPolling = useCallback(() => {
		// Clear any existing polling interval
		if (pollingIntervalRef.current) {
			clearInterval(pollingIntervalRef.current);
		}

		// Poll every 3 seconds
		pollingIntervalRef.current = setInterval(async () => {
			const hasProcessing = await fetchUploadedFiles(true); // Silent refresh

			// Stop polling if no files are processing
			if (!hasProcessing && pollingIntervalRef.current) {
				clearInterval(pollingIntervalRef.current);
				pollingIntervalRef.current = null;
			}
		}, 3000);
	}, [fetchUploadedFiles]);

	// Stop polling when component unmounts
	useEffect(() => {
		return () => {
			if (pollingIntervalRef.current) {
				clearInterval(pollingIntervalRef.current);
			}
		};
	}, []);

	// Drop handler
	const handleDrop = useCallback((droppedFiles) => {
		setFiles(droppedFiles);
	}, []);

	// Upload handler with progress tracking
	const handleUpload = useCallback(async () => {
		setUploading(true);
		const totalFiles = files.length;

		// Reset progress
		setUploadProgress({
			current: 0,
			total: totalFiles,
			stage: null,
			percentage: 0,
			fileName: null,
		});

		try {
			let successCount = 0;
			let failCount = 0;
			const uploadedDocIds = [];

			// Process each file with progress tracking
			for (let i = 0; i < files.length; i++) {
				const file = files[i];
				const fileIndex = i + 1;

				try {
					// Stage 1: Uploading to S3
					setUploadProgress({
						current: fileIndex,
						total: totalFiles,
						stage: "s3",
						percentage: 10,
						fileName: file.name,
					});

					// Call the endpoint that uploads to S3 and starts background chunking
					const response = await docApi.uploadAndParse(userId, file);

					if (response.status === "success") {
						// Stage 2: Saved to MongoDB
						setUploadProgress({
							current: fileIndex,
							total: totalFiles,
							stage: "mongodb",
							percentage: 30,
							fileName: file.name,
						});

						successCount++;
						uploadedDocIds.push(response.document._id);

						// Small delay to show mongodb stage
						await new Promise((resolve) =>
							setTimeout(resolve, 300)
						);
					}
				} catch (error) {
					failCount++;
					console.error(`Failed to upload ${file.name}:`, error);
					toast.error(
						`${file.name}: ${
							error.response?.data?.detail || "Upload failed"
						}`
					);
				}
			}

			// Stage 3: Start chunking phase
			if (successCount > 0) {
				setUploadProgress({
					current: successCount,
					total: totalFiles,
					stage: "chunking",
					percentage: 50,
					fileName: `${successCount} file${
						successCount > 1 ? "s" : ""
					}`,
				});

				setFiles([]);

				// Refresh the file list to show uploaded documents
				await fetchUploadedFiles(true); // Silent refresh

				// Start polling to track chunking progress
				startPolling();

				// Poll for chunking completion
				const checkChunking = setInterval(async () => {
					const response = await docApi.getAllDocs(userId);
					const filesArray = Object.values(response);

					// Check if all uploaded files are chunked
					const allChunked = uploadedDocIds.every((docId) => {
						const doc = filesArray.find((f) => f._id === docId);
						return doc && doc.chunked === true;
					});

					if (allChunked) {
						clearInterval(checkChunking);

						// Stage 4: Complete
						setUploadProgress({
							current: successCount,
							total: totalFiles,
							stage: "complete",
							percentage: 100,
							fileName: null,
						});

						toast.success(
							`Successfully processed ${successCount} file(s)!`
						);

						// Final refresh to update UI
						await fetchUploadedFiles();

						// Reset progress after showing complete state
						setTimeout(() => {
							setUploadProgress({
								current: 0,
								total: 0,
								stage: null,
								percentage: 0,
								fileName: null,
							});
						}, 2000);
					}
				}, 2000);

				// Timeout after 5 minutes
				setTimeout(() => {
					clearInterval(checkChunking);
					if (uploadProgress.stage === "chunking") {
						toast.warning(
							"Chunking is taking longer than expected. Files will continue processing in the background."
						);
						setUploadProgress({
							current: 0,
							total: 0,
							stage: null,
							percentage: 0,
							fileName: null,
						});
					}
				}, 5 * 60 * 1000);
			}

			if (failCount > 0) {
				toast.error(`Failed to upload ${failCount} file(s)`);
			}
		} catch (error) {
			console.error("Upload error:", error);
			toast.error("Failed to upload files");
		} finally {
			setUploading(false);
		}
	}, [files, userId, fetchUploadedFiles, startPolling, uploadProgress.stage]);

	// Download handler
	const handleDownload = useCallback(async (s3_path, fileName) => {
		try {
			const response = await s3Api.downloadFile(s3_path);
			const url = window.URL.createObjectURL(response);
			const link = document.createElement("a");
			link.href = url;
			link.download = fileName || s3_path.split("/").pop();
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
			window.URL.revokeObjectURL(url);
			toast.success("File downloaded successfully");
		} catch (error) {
			console.error("Download error:", error);
			toast.error(
				error.response?.data?.detail || "Failed to download file"
			);
		}
	}, []);

	// Delete handler
	const handleDelete = useCallback(
		async (s3_path) => {
			try {
				await s3Api.deleteFile(s3_path);
				await docApi.deleteDoc(userId, s3_path);
				const updatedFiles = uploadedFiles.filter(
					(file) => file.s3_path !== s3_path
				);
				setUploadedFiles(updatedFiles);
				updateUserDocList(updatedFiles); // Update global user doc_list
				toast.success("File deleted successfully");
			} catch (error) {
				console.error("Delete error:", error);
				toast.error(
					error.response?.data?.detail || "Failed to delete file"
				);
			}
		},
		[userId, uploadedFiles]
	);

	return {
		files,
		setFiles,
		uploading,
		uploadedFiles,
		loading,
		uploadProgress,
		handleDrop,
		handleUpload,
		handleDownload,
		handleDelete,
		fetchUploadedFiles,
	};
};
