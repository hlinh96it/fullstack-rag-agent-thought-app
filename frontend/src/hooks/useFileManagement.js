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
		stage: null, // 's3', 'mongodb', 'chunking', 'indexing', 'complete'
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
		async (silent = false, updateProgress = false) => {
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
				// Backend returns chunked as boolean: true (done) or false (processing)
				// Backend returns indexed as boolean: true (done) or false (processing)
				const chunkingFiles = sortedFiles.filter(
					(file) => file.chunked === false
				);
				const indexingFiles = sortedFiles.filter(
					(file) => file.chunked === true && file.indexed === false
				);

				const hasChunking = chunkingFiles.length > 0;
				const hasIndexing = indexingFiles.length > 0;

				if (silent && (hasChunking || hasIndexing)) {
					console.log(
						`[Fetch] Processing status - Chunking: ${chunkingFiles.length}, Indexing: ${indexingFiles.length}`,
						{
							chunking: chunkingFiles.map((f) => ({
								title: f.title,
								chunked: f.chunked,
							})),
							indexing: indexingFiles.map((f) => ({
								title: f.title,
								indexed: f.indexed,
							})),
						}
					);
				}

				// Update progress bar based on backend status
				if (updateProgress) {
					if (hasChunking) {
						setUploadProgress((prev) => ({
							...prev,
							stage: "chunking",
							percentage: 40,
						}));
					} else if (hasIndexing) {
						setUploadProgress((prev) => ({
							...prev,
							stage: "indexing",
							percentage: 70,
						}));
					} else if (
						!hasChunking &&
						!hasIndexing &&
						sortedFiles.length > 0
					) {
						// All files are processed
						setUploadProgress((prev) => ({
							...prev,
							stage: "complete",
							percentage: 100,
						}));
					}
				}

				return hasChunking || hasIndexing;
			} catch (error) {
				console.error("Error fetching files:", error);

				// Handle timeout errors specifically
				if (error.message?.includes("timeout")) {
					if (!silent) {
						toast.error(
							"Request timed out. Please check your connection or try again."
						);
					}
					// Stop polling on timeout to avoid repeated failures
					if (pollingIntervalRef.current) {
						clearInterval(pollingIntervalRef.current);
						pollingIntervalRef.current = null;
					}
				} else if (!silent && error.status !== 500) {
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
			pollingIntervalRef.current = null;
		}

		console.log("[Polling] Starting to monitor processing status...");

		let consecutiveErrors = 0;
		const maxErrors = 3;

		// Poll every 3 seconds
		pollingIntervalRef.current = setInterval(async () => {
			try {
				const hasProcessing = await fetchUploadedFiles(true, true); // Silent refresh with progress update
				consecutiveErrors = 0; // Reset error counter on success

				// Stop polling if no files are processing
				if (!hasProcessing) {
					console.log(
						"[Polling] All files processed. Stopping polling."
					);
					if (pollingIntervalRef.current) {
						clearInterval(pollingIntervalRef.current);
						pollingIntervalRef.current = null;
					}
					toast.success("All files processed successfully!");

					// Set final complete stage
					setUploadProgress((prev) => ({
						...prev,
						stage: "complete",
						percentage: 100,
					}));

					// Reset progress bar after showing complete
					setTimeout(() => {
						setUploadProgress({
							current: 0,
							total: 0,
							stage: null,
							percentage: 0,
							fileName: null,
						});
					}, 3000);
				} else {
					console.log("[Polling] Still processing files...");
				}
			} catch (error) {
				consecutiveErrors++;
				console.warn(
					`[Polling] Error (${consecutiveErrors}/${maxErrors}):`,
					error
				);

				// Stop polling after max consecutive errors
				if (consecutiveErrors >= maxErrors) {
					console.log(
						"[Polling] Max errors reached. Stopping polling."
					);
					if (pollingIntervalRef.current) {
						clearInterval(pollingIntervalRef.current);
						pollingIntervalRef.current = null;
					}
					toast.warning(
						"Stopped checking file status due to connection issues. Please refresh to check status."
					);
				}
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
							percentage: 20,
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

			// After S3/MongoDB upload is complete
			if (successCount > 0) {
				// Set chunking stage
				setUploadProgress({
					current: successCount,
					total: totalFiles,
					stage: "chunking",
					percentage: 40,
					fileName: `${successCount} file${
						successCount > 1 ? "s" : ""
					}`,
				});

				setFiles([]);

				// Immediately fetch and display the uploaded files
				// This will show them with chunked=false and indexed=false (processing state)
				await fetchUploadedFiles(true); // Silent refresh to show files immediately

				// Start polling to update file status indicators AND progress bar in the background
				// Files will show spinners/processing indicators based on chunked/indexed status
				startPolling();

				toast.success(
					`${successCount} file(s) uploaded! Chunking and indexing in background...`
				);
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
	}, [files, userId, fetchUploadedFiles, startPolling]);

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
