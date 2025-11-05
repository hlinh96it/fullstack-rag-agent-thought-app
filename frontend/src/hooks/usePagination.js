import { useState, useEffect, useRef } from "react";

export const usePagination = (totalItems, initialItemsPerPage = 5) => {
	const [currentPage, setCurrentPage] = useState(1);
	const [itemsPerPage, setItemsPerPage] = useState(initialItemsPerPage);
	const containerRef = useRef(null);

	// Calculate items per page based on viewport
	useEffect(() => {
		const calculateItemsPerPage = () => {
			if (containerRef.current) {
				const containerTop =
					containerRef.current.getBoundingClientRect().top;
				const availableHeight = window.innerHeight - containerTop - 80;
				const itemHeight = 80;
				setItemsPerPage(
					Math.max(3, Math.floor(availableHeight / itemHeight))
				);
			}
		};
		calculateItemsPerPage();
		window.addEventListener("resize", calculateItemsPerPage);
		return () =>
			window.removeEventListener("resize", calculateItemsPerPage);
	}, []);

	const totalPages = Math.ceil(totalItems / itemsPerPage);

	const goToNextPage = () => {
		setCurrentPage((prev) => Math.min(totalPages, prev + 1));
	};

	const goToPreviousPage = () => {
		setCurrentPage((prev) => Math.max(1, prev - 1));
	};

	const goToPage = (page) => {
		setCurrentPage(page);
	};

	const getPaginatedItems = (items) => {
		const startIndex = (currentPage - 1) * itemsPerPage;
		const endIndex = startIndex + itemsPerPage;
		return items.slice(startIndex, endIndex);
	};

	// Reset to first page when total items change significantly
	useEffect(() => {
		if (currentPage > totalPages && totalPages > 0) {
			setCurrentPage(1);
		}
	}, [totalPages, currentPage]);

	return {
		currentPage,
		itemsPerPage,
		totalPages,
		containerRef,
		goToNextPage,
		goToPreviousPage,
		goToPage,
		getPaginatedItems,
	};
};
