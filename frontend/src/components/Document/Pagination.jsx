import React from 'react';
import { Button } from '@/components/ui/button';

const Pagination = ({
    currentPage,
    totalPages,
    totalItems,
    onNext,
    onPrevious,
    onPageSelect
}) => {
    if (totalItems === 0) return null;

    return (
        <div className="flex items-center gap-2">
            <p className="text-sm text-gray-500">
                Total: {totalItems} file{totalItems > 1 ? 's' : ''}
            </p>
            <Button
                variant="outline"
                size="sm"
                onClick={onPrevious}
                disabled={currentPage === 1}
            >
                Previous
            </Button>
            <div className="flex items-center gap-1">
                {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                    <Button
                        key={page}
                        variant={currentPage === page ? "default" : "outline"}
                        size="sm"
                        onClick={() => onPageSelect(page)}
                        className="min-w-9 h-8"
                    >
                        {page}
                    </Button>
                ))}
            </div>
            <Button
                variant="outline"
                size="sm"
                onClick={onNext}
                disabled={currentPage === totalPages}
            >
                Next
            </Button>
        </div>
    );
};

export default Pagination;
