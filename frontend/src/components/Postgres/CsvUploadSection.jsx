import React, { useState } from "react";
import { Dropzone, DropzoneContent, DropzoneEmptyState } from '@/components/ui/shadcn-io/dropzone';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { postgresApi } from "@/api/postgres";
import { Loader2, Upload, Database, CheckCircle2 } from "lucide-react";

const CsvUploadSection = ({ userId, onUploadSuccess }) => {
    const [files, setFiles] = useState([]);
    const [tableName, setTableName] = useState("");
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);

    const handleDrop = (acceptedFiles) => {
        if (acceptedFiles && acceptedFiles.length > 0) {
            setFiles(acceptedFiles);
            // Auto-fill table name from first file if empty
            if (!tableName && acceptedFiles[0]) {
                const nameWithoutExt = acceptedFiles[0].name.replace(/\.csv$/i, "");
                setTableName(nameWithoutExt);
            }
        }
    };

    const handleUpload = async () => {
        if (!files || files.length === 0 || !userId) return;

        setIsUploading(true);
        setUploadProgress(0);

        try {
            const file = files[0]; // Only upload first file
            const response = await postgresApi.uploadCsv(
                userId,
                file,
                tableName,
                (progress) => setUploadProgress(progress)
            );

            toast.success(`Table '${response.table_name}' created successfully!`);
            setFiles([]);
            setTableName("");
            setUploadProgress(0);

            if (onUploadSuccess) {
                onUploadSuccess();
            }
        } catch (error) {
            console.error("Upload failed:", error);
            toast.error(error.message || "Failed to upload CSV file");
            setUploadProgress(0);
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <>
            <Dropzone
                accept={{ 'text/csv': ['.csv'] }}
                maxFiles={1}
                maxSize={1024 * 1024 * 10} // 10MB
                onDrop={handleDrop}
                onError={(error) => toast.error(error?.message || 'File upload error')}
                src={files}
                className='flex max-h-30 w-full cursor-pointer'
            >
                <DropzoneEmptyState />
                <DropzoneContent />
            </Dropzone>

            {/* Table Name Input */}
            {files.length > 0 && (
                <div className="space-y-2">
                    <label className="text-sm font-medium">Table Name (Optional)</label>
                    <Input
                        value={tableName}
                        onChange={(e) => setTableName(e.target.value)}
                        placeholder="Enter table name or use filename"
                        disabled={isUploading}
                    />
                </div>
            )}

            {/* Progress Bar */}
            <div className={`w-full space-y-3 transition-opacity duration-300 ${isUploading ? 'opacity-100' : 'opacity-30'
                }`}>
                <div className="space-y-2 transition-all">
                    <Progress value={isUploading ? uploadProgress : 0} className="h-2" />

                    <div className="flex items-center justify-between text-sm">
                        <div className={`flex items-center gap-2 ${uploadProgress === 100 ? 'text-emerald-600' : 'text-blue-600'
                            }`}>
                            {uploadProgress === 100 ? (
                                <>
                                    <CheckCircle2 className="h-4 w-4" />
                                    <span className="font-medium">Complete!</span>
                                </>
                            ) : (
                                <>
                                    <Database className="h-4 w-4" />
                                    <span className="font-medium">Creating PostgreSQL Table</span>
                                </>
                            )}
                        </div>
                        <div className="text-gray-600">
                            {uploadProgress}%
                        </div>
                    </div>
                </div>
            </div>

            {/* Upload Button */}
            <Button
                onClick={handleUpload}
                disabled={isUploading || files.length === 0}
                className={`w-full sm:w-auto transition-opacity duration-300 cursor-pointer ${files.length === 0 ? 'opacity-30' : 'opacity-100'
                    }`}
            >
                {isUploading ? (
                    <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Uploading...
                    </>
                ) : (
                    <>
                        <Upload className="mr-2 h-4 w-4" />
                        Upload {files.length} CSV file
                    </>
                )}
            </Button>
        </>
    );
};

export default CsvUploadSection;
