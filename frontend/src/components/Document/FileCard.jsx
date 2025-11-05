import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { FileText, Download, Trash2, BadgeCheckIcon, BadgeXIcon, Calendar, RulerDimensionLine, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

const FileCard = ({ file, onDownload, onDelete }) => {
    return (
        <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="flex items-start justify-between p-4 gap-3 py-0">
                <div className="flex items-start gap-5 flex-1 min-w-0">
                    <FileText className="h-5 w-5 text-blue-500 shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium wrap-break-words">
                            {file.title.split('/').pop()}
                        </p>
                        <p className="text-xs text-gray-500 mt-1 space-x-2">
                            {file.indexed ? (
                                <Badge variant='secondary' className="bg-blue-500 text-white dark:bg-blue-600">
                                    <BadgeCheckIcon /> Indexed
                                </Badge>
                            ) : (
                                <Badge variant='secondary' className="bg-red-500 text-white dark:bg-red-600">
                                    <BadgeXIcon /> Not Indexed
                                </Badge>
                            )}
                            {file.chunked === 'processing' ? (
                                <Badge variant='secondary' className="bg-yellow-500 text-white dark:bg-yellow-600">
                                    <Loader2 className="h-3 w-3 animate-spin mr-1" /> Chunking...
                                </Badge>
                            ) : file.chunked === true ? (
                                <Badge variant='secondary' className="bg-blue-500 text-white dark:bg-blue-600">
                                    <BadgeCheckIcon /> Chunked
                                </Badge>
                            ) : (
                                <Badge variant='secondary' className="bg-red-500 text-white dark:bg-red-600">
                                    <BadgeXIcon /> Not Chunked
                                </Badge>
                            )}
                            {file.size ? (
                                <Badge variant='secondary'>
                                    <RulerDimensionLine /> {(file.size / 1024).toFixed(2)} KB
                                </Badge>
                            ) : (
                                <Badge>Size unknown</Badge>
                            )}
                            {file.uploaded_date ? (
                                <Badge variant='secondary'>
                                    <Calendar /> Uploaded date: {new Date(file.uploaded_date).toLocaleDateString()}
                                </Badge>
                            ) : (
                                <Badge><Calendar /> Date unknown</Badge>
                            )}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDownload(file.s3_path, file.title)}
                        className="text-blue-500 hover:text-blue-700 hover:bg-blue-50 cursor-pointer"
                    >
                        <Download className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDelete(file.s3_path)}
                        className="text-red-500 hover:text-red-700 hover:bg-red-50 cursor-pointer"
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
};

export default FileCard;
