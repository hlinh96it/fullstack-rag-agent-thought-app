import React from 'react';
import { Loader2 } from 'lucide-react';
import FileCard from './FileCard';
import Pagination from './Pagination';

const FileListSection = ({
    uploadedFiles,
    loading,
    currentPage,
    totalPages,
    itemsPerPage,
    containerRef,
    onDownload,
    onDelete,
    onNextPage,
    onPreviousPage,
    onPageSelect
}) => {
    const paginatedFiles = uploadedFiles.slice(
        (currentPage - 1) * itemsPerPage,
        currentPage * itemsPerPage
    );

    return (
        <div className='flex flex-col gap-4 mt-6' ref={containerRef}>
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <h3 className='text-xl font-semibold'>Uploaded Files</h3>
                </div>
                <Pagination
                    currentPage={currentPage}
                    totalPages={totalPages}
                    totalItems={uploadedFiles.length}
                    onNext={onNextPage}
                    onPrevious={onPreviousPage}
                    onPageSelect={onPageSelect}
                />
            </div>
            <div
                className="overflow-y-auto pb-4"
                style={{ maxHeight: `${itemsPerPage * 80}px` }}
            >
                {loading ? (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                    </div>
                ) : uploadedFiles.length > 0 ? (
                    <div className="grid gap-3">
                        {paginatedFiles.map((file, index) => (
                            <FileCard
                                key={index}
                                file={file}
                                onDownload={onDownload}
                                onDelete={onDelete}
                            />
                        ))}
                    </div>
                ) : (
                    <p className="text-sm text-gray-500 py-8 text-center">No files uploaded yet</p>
                )}
            </div>
        </div>
    );
};

export default FileListSection;
