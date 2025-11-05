import React, { useEffect } from 'react';
import { useAppContext } from '@/context/AppContext';
import { useFileManagement } from '@/hooks/useFileManagement';
import { usePagination } from '@/hooks/usePagination';
import FileUploadSection from './Document/FileUploadSection';
import FileListSection from './Document/FileListSection';

const Document = () => {
    const { user } = useAppContext();

    const {
        files, uploading, uploadedFiles, loading, uploadProgress,
        handleDrop, handleUpload, handleDownload, handleDelete, fetchUploadedFiles
    } = useFileManagement(user._id);

    const {
        currentPage, itemsPerPage, totalPages, containerRef,
        goToNextPage, goToPreviousPage, goToPage
    } = usePagination(uploadedFiles.length);

    // Initial fetch
    useEffect(() => {
        if (user._id) {
            fetchUploadedFiles();
        }
    }, [user._id, fetchUploadedFiles]);

    return (
        <div className='flex flex-col w-full p-10 gap-6'>
            <FileUploadSection
                files={files} uploading={uploading} uploadProgress={uploadProgress}
                onDrop={handleDrop} onUpload={handleUpload}
            />
            <FileListSection
                uploadedFiles={uploadedFiles} loading={loading} currentPage={currentPage}
                totalPages={totalPages} itemsPerPage={itemsPerPage} containerRef={containerRef}
                onDownload={handleDownload} onDelete={handleDelete} onNextPage={goToNextPage}
                onPreviousPage={goToPreviousPage} onPageSelect={goToPage}
            />
        </div>
    );
};

export default Document;
