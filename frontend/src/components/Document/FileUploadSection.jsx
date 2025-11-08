import React from 'react';
import { Dropzone, DropzoneContent, DropzoneEmptyState } from '@/components/ui/shadcn-io/dropzone';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Loader2, Upload, Cloud, Database, Sparkles, Layers, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';

const FileUploadSection = ({ files, uploading, uploadProgress, onDrop, onUpload }) => {
    // Get stage info for display
    const getStageInfo = () => {
        switch (uploadProgress.stage) {
            case 's3':
                return { icon: Cloud, label: 'Uploading to S3', color: 'text-blue-500' };
            case 'mongodb':
                return { icon: Database, label: 'Saving to Database', color: 'text-green-500' };
            case 'chunking':
                return { icon: Sparkles, label: 'Processing & Chunking', color: 'text-purple-500' };
            case 'indexing':
                return { icon: Layers, label: 'Indexing to Vector Store', color: 'text-orange-500' };
            case 'complete':
                return { icon: CheckCircle2, label: 'Complete!', color: 'text-emerald-500' };
            default:
                return { icon: Cloud, label: 'Waiting to Upload', color: 'text-gray-500' };
        }
    };

    const stageInfo = getStageInfo();
    return (
        <>
            <div className='flex flex-col gap-2'>
                <h2 className='text-2xl font-semibold'>Upload Documents</h2>
                <p className='text-sm text-gray-500'>
                    Upload PDF or image files (PNG, JPG, JPEG, GIF, WEBP). Maximum 5 files, each up to 5MB.
                </p>
            </div>
            <Dropzone
                accept={{
                    'application/pdf': ['.pdf'],
                    'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp']
                }}
                maxFiles={5}
                minSize={1024}
                maxSize={1024 * 1024 * 5}
                onDrop={onDrop}
                onError={toast.error}
                src={files}
                className='flex max-h-30 w-full cursor-pointer'
            >
                <DropzoneEmptyState />
                <DropzoneContent />
            </Dropzone>

            {/* Progress Bar - Always visible */}
            <div className={`w-full space-y-3 transition-opacity duration-300 ${uploading && uploadProgress.stage ? 'opacity-100' : 'opacity-30'}`}>
                {/* Progress Bar */}
                <div className="space-y-2 transition-all">
                    <Progress value={uploading ? uploadProgress.percentage : 0} className="h-2" />

                    {/* Stage Info */}
                    {stageInfo && (
                        <div className="flex items-center justify-between text-sm">
                            <div className={`flex items-center gap-2 ${stageInfo.color}`}>
                                {React.createElement(stageInfo.icon, { className: "h-4 w-4" })}
                                <span className="font-medium">{stageInfo.label}</span>
                            </div>

                            <div className="text-gray-600">
                                {uploadProgress.stage === 'complete' ? (
                                    <span className="text-emerald-600 font-medium">
                                        {uploadProgress.current}/{uploadProgress.total} files processed
                                    </span>
                                ) : (
                                    <>
                                        {uploadProgress.current}/{uploadProgress.total} files
                                        {uploadProgress.fileName && (
                                            <span className="ml-2 text-gray-500">
                                                • {uploadProgress.fileName}
                                            </span>
                                        )}
                                    </>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Stage Indicators */}
                    <div className="flex items-center justify-between text-xs text-gray-500 pt-1">
                        <div className={`flex items-center gap-1 transition-colors duration-300 ${uploadProgress.stage === 's3'
                            ? 'text-blue-600 font-medium'
                            : uploadProgress.percentage > 10
                                ? 'text-blue-300'
                                : ''
                            }`}>
                            <Cloud className="h-3 w-3" />
                            <span>S3</span>
                        </div>
                        <div className={`flex items-center gap-1 transition-colors duration-300 ${uploadProgress.stage === 'mongodb'
                            ? 'text-green-600 font-medium'
                            : uploadProgress.percentage > 20
                                ? 'text-green-300'
                                : ''
                            }`}>
                            <Database className="h-3 w-3" />
                            <span>Database</span>
                        </div>
                        <div className={`flex items-center gap-1 transition-colors duration-300 ${uploadProgress.stage === 'chunking'
                            ? 'text-purple-600 font-medium'
                            : uploadProgress.percentage > 40
                                ? 'text-purple-300'
                                : ''
                            }`}>
                            <Sparkles className="h-3 w-3" />
                            <span>Chunking</span>
                        </div>
                        <div className={`flex items-center gap-1 transition-colors duration-300 ${uploadProgress.stage === 'indexing'
                            ? 'text-orange-600 font-medium'
                            : uploadProgress.percentage > 70
                                ? 'text-orange-300'
                                : ''
                            }`}>
                            <Layers className="h-3 w-3" />
                            <span>Indexing</span>
                        </div>
                        <div className={`flex items-center gap-1 transition-colors duration-300 ${uploadProgress.stage === 'complete' || uploadProgress.percentage === 100
                            ? 'text-emerald-600 font-medium'
                            : ''
                            }`}>
                            <CheckCircle2 className="h-3 w-3" />
                            <span>Complete</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Upload Button - Always visible */}
            <Button
                onClick={onUpload}
                disabled={uploading || files.length === 0}
                className={`w-full sm:w-auto transition-opacity duration-300 cursor-pointer ${files.length === 0 ? 'opacity-30' : 'opacity-100'
                    }`}
            >
                {uploading ? (
                    <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Uploading...
                    </>
                ) : (
                    <>
                        <Upload className="mr-2 h-4 w-4" />
                        Upload {files.length} file{files.length > 1 ? 's' : ''}
                    </>
                )}
            </Button>
        </>
    );
};

export default FileUploadSection;
