import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { FileText, Download, Trash2, BadgeCheckIcon, BadgeXIcon, Calendar, RulerDimensionLine, Loader2, Sparkles, Layers } from 'lucide-react';
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
                            {/* Chunking Status */}
                            {file.chunked === false ? (
                                <Badge variant='secondary' className="bg-purple-500 text-white dark:bg-purple-600">
                                    <Sparkles className="h-3 w-3 mr-1" />
                                    <Loader2 className="h-3 w-3 animate-spin mr-1" /> Chunking...
                                </Badge>
                            ) : file.chunked === true ? (
                                <Badge variant='secondary' className="bg-green-500 text-white dark:bg-green-600">
                                    <BadgeCheckIcon className="h-3 w-3 mr-1" /> Chunked
                                </Badge>
                            ) : (
                                <Badge variant='secondary' className="bg-gray-500 text-white dark:bg-gray-600">
                                    <BadgeXIcon className="h-3 w-3 mr-1" /> Chunk Status Unknown
                                </Badge>
                            )}

                            {/* Indexing Status */}
                            {file.chunked === true && file.indexed === false ? (
                                <Badge variant='secondary' className="bg-orange-500 text-white dark:bg-orange-600">
                                    <Layers className="h-3 w-3 mr-1" />
                                    <Loader2 className="h-3 w-3 animate-spin mr-1" /> Indexing...
                                </Badge>
                            ) : file.indexed === true ? (
                                <Badge variant='secondary' className="bg-blue-500 text-white dark:bg-blue-600">
                                    <BadgeCheckIcon className="h-3 w-3 mr-1" /> Indexed
                                </Badge>
                            ) : file.chunked === true && file.indexed !== false ? (
                                <Badge variant='secondary' className="bg-gray-500 text-white dark:bg-gray-600">
                                    <BadgeXIcon className="h-3 w-3 mr-1" /> Index Status Unknown
                                </Badge>
                            ) : null}

                            {/* File Size */}
                            {file.size ? (
                                <Badge variant='secondary'>
                                    <RulerDimensionLine className="h-3 w-3 mr-1" /> {(file.size / 1024).toFixed(2)} MB
                                </Badge>
                            ) : (
                                <Badge variant='secondary'>Size unknown</Badge>
                            )}

                            {/* Upload Date */}
                            {file.uploaded_date ? (
                                <Badge variant='secondary'>
                                    <Calendar className="h-3 w-3 mr-1" /> {new Date(file.uploaded_date * 1000).toLocaleDateString()}
                                </Badge>
                            ) : (
                                <Badge variant='secondary'><Calendar className="h-3 w-3 mr-1" /> Date unknown</Badge>
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
