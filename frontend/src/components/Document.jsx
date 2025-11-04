import { Dropzone, DropzoneContent, DropzoneEmptyState } from '@/components/ui/shadcn-io/dropzone'
import React, { useState, useEffect } from 'react'
import { apiS3, apiUser } from '@/lib/axios'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Loader2, Upload, Trash2, FileText, Download } from 'lucide-react'
import { useAppContext } from '@/context/AppContext'
import { toast } from 'sonner';
import { s3Api } from '@/api/s3'
import { docApi } from '@/api/doc'


const Document = () => {
    const { user } = useAppContext()
    const [files, setFiles] = useState([])
    const [uploading, setUploading] = useState(false)
    const [uploadedFiles, setUploadedFiles] = useState([])
    const [loading, setLoading] = useState(false)
    const [currentPage, setCurrentPage] = useState(1)
    const [filesPerPage, setFilesPerPage] = useState(5)
    const containerRef = React.useRef(null)

    const fetchUploadedFiles = async () => {
        setLoading(true)

        try {
            const response = await docApi.getAllDocs(user._id)
            const filesArray = Object.values(response)

            // Sort by uploaded_date in descending order (newest first)
            const sortedFiles = filesArray.sort((a, b) => {
                const dateA = a.uploaded_date || 0
                const dateB = b.uploaded_date || 0
                return dateB - dateA
            })

            setUploadedFiles(sortedFiles)
            toast.success(`Loaded ${sortedFiles.length} files`)

        } catch (error) {
            console.error('Error fetching files:', error)
            if (error.response?.status !== 500) {
                toast.error('Failed to fetch uploaded files')
            }
        } finally {
            setLoading(false)
        }
    }

    const handleDrop = (files) => {
        setFiles(files)
    }

    const handleUpload = async () => {
        setUploading(true)
        const formData = new FormData()

        files.forEach((file) => {
            formData.append('files', file)
        })

        try {
            const response = await s3Api.uploadFiles(user._id, formData)
            console.log(response)

            if (response.uploaded > 0) {
                toast.success(`Successfully uploaded ${response.uploaded} file(s)`)

                // Update uploaded files to user's doc_list in database
                try {
                    const newDocs = response.uploaded_files.map(file => ({
                        title: file.original_filename, s3_path: file.s3_key, size: file.size,
                        uploaded_date: Date.now(), indexed: false, chunked: false
                    }))
                    console.log(newDocs)
                    const updateResponse = await docApi.addDoc(user._id, newDocs)
                    setUploadedFiles(prevFiles => [...updateResponse, ...prevFiles])
                    console.log(uploadedFiles)

                    // Reset to first page after upload
                    setCurrentPage(1)

                } catch (error) {
                    console.error('Failed to update user doc_list:', error)
                    toast.error('Files uploaded but failed to update user database')
                }

                setFiles([])
                fetchUploadedFiles()
            }

            if (response.failed > 0) {
                response.failed_files.forEach(failed => {
                    toast.error(`${failed.filename}: ${failed.error}`)
                })
            }

        } catch (error) {
            console.error('Upload error:', error)
            toast.error(error.response?.detail || 'Failed to upload files')
        } finally {
            setUploading(false)
        }
    }

    const handleDownload = async (s3_path, fileName) => {
        try {
            const response = await s3Api.downloadFile(s3_path)

            // Create a blob URL and trigger download
            // The response is already a blob with the correct content type
            const url = window.URL.createObjectURL(response)
            const link = document.createElement('a')
            link.href = url
            link.download = fileName || s3_path.split('/').pop()
            document.body.appendChild(link)
            link.click()

            // Cleanup
            document.body.removeChild(link)
            window.URL.revokeObjectURL(url)

            toast.success('File downloaded successfully')
        } catch (error) {
            console.error('Download error:', error)
            toast.error(error.response?.data?.detail || 'Failed to download file')
        }
    }

    const handleDelete = async (s3_path) => {
        try {
            await s3Api.deleteFile(s3_path)
            await docApi.deleteDoc(user._id, s3_path)

            toast.success('File deleted successfully')

            // Refresh the file list
            fetchUploadedFiles()

        } catch (error) {
            console.error('Delete error:', error)
            toast.error(error.response?.data?.detail || 'Failed to delete file')
        }
    }

    useEffect(() => {
        if (user._id) {
            fetchUploadedFiles()
        }
    }, [user?._id, user?.id])

    // Calculate files per page based on available viewport height
    useEffect(() => {
        const calculateFilesPerPage = () => {
            if (containerRef.current) {
                // Get the position of the container from the top of the viewport
                const containerTop = containerRef.current.getBoundingClientRect().top

                // Calculate available height (from container to bottom of viewport minus padding)
                const availableHeight = window.innerHeight - containerTop - 80 // 80px for bottom padding/spacing

                const cardHeight = 80 // Approximate height of each card with gap
                const calculatedFiles = Math.max(3, Math.floor(availableHeight / cardHeight))
                setFilesPerPage(calculatedFiles)
            }
        }

        calculateFilesPerPage()
        window.addEventListener('resize', calculateFilesPerPage)

        return () => window.removeEventListener('resize', calculateFilesPerPage)
    }, [])

    return (
        <div className='flex flex-col w-full p-10 gap-6'>
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
                maxFiles={5} minSize={1024} maxSize={1024 * 1024 * 5}
                onDrop={handleDrop} onError={toast.error} src={files}
                className='flex max-h-30 w-full cursor-pointer'
            >
                <DropzoneEmptyState />
                <DropzoneContent />
            </Dropzone>

            <Button
                onClick={handleUpload}
                disabled={uploading || files.length === 0}
                className={`w-full sm:w-auto ${files.length === 0 ? 'opacity-50' : ''}`}
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

            {/* Uploaded Files List */}
            <div className='flex flex-col gap-4 mt-6' ref={containerRef}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <h3 className='text-xl font-semibold'>Uploaded Files</h3>

                    </div>

                    {/* Pagination Controls - Always visible when there are files */}
                    {uploadedFiles.length > 0 && (
                        <div className="flex items-center gap-2">
                            {uploadedFiles.length > 0 && (
                                <p className="text-sm text-gray-500">
                                    Total: {uploadedFiles.length} file{uploadedFiles.length > 1 ? 's' : ''}
                                </p>
                            )}
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                                disabled={currentPage === 1}
                            >

                                Previous
                            </Button>

                            <div className="flex items-center gap-1">
                                {Array.from({ length: Math.ceil(uploadedFiles.length / filesPerPage) }, (_, i) => i + 1).map(page => (
                                    <Button
                                        key={page}
                                        variant={currentPage === page ? "default" : "outline"}
                                        size="sm"
                                        onClick={() => setCurrentPage(page)}
                                        className="min-w-9 h-8"
                                    >
                                        {page}
                                    </Button>
                                ))}
                            </div>

                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setCurrentPage(prev => Math.min(Math.ceil(uploadedFiles.length / filesPerPage), prev + 1))}
                                disabled={currentPage === Math.ceil(uploadedFiles.length / filesPerPage)}
                            >
                                Next
                            </Button>
                        </div>
                    )}
                </div>

                {/* Scrollable container for file list */}
                <div
                    className="overflow-y-auto pb-4"
                    style={{ maxHeight: `${filesPerPage * 80}px` }}
                >
                    {loading ? (
                        <div className="flex items-center justify-center py-8">
                            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                        </div>
                    ) : uploadedFiles.length > 0 ? (
                        <>
                            <div className="grid gap-3">
                                {uploadedFiles
                                    .slice((currentPage - 1) * filesPerPage, currentPage * filesPerPage)
                                    .map((file, index) => (
                                        <Card key={index} className="hover:shadow-md transition-shadow cursor-pointer">

                                            <CardContent className="flex items-start justify-between p-4 gap-3 py-0">

                                                <div className="flex items-start gap-5 flex-1 min-w-0">
                                                    <FileText className="h-5 w-5 text-blue-500 shrink-0 mt-0.5" />
                                                    <div className="flex-1 min-w-0">
                                                        <p className="text-sm font-medium wrap-break-words">
                                                            {file.title.split('/').pop()}
                                                        </p>
                                                        <p className="text-xs text-gray-500 mt-1">
                                                            {file.size ? `${(file.size / 1024).toFixed(2)} KB` : 'Size unknown'}   •   Uploaded date: {file.uploaded_date ? new Date(file.uploaded_date).toLocaleDateString() : 'Date unknown'}
                                                        </p>
                                                    </div>
                                                </div>

                                                {/* Delete and Download button */}

                                                <div className="flex items-center gap-2 shrink-0">
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => handleDownload(file.s3_path, file.title)}
                                                        className="text-blue-500 hover:text-blue-700 hover:bg-blue-50 cursor-pointer"
                                                    >
                                                        <Download className="h-4 w-4" />
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => handleDelete(file.s3_path)}
                                                        className="text-red-500 hover:text-red-700 hover:bg-red-50 cursor-pointer"
                                                    >
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    ))}
                            </div>
                        </>
                    ) : (
                        <p className="text-sm text-gray-500 py-8 text-center">
                            No files uploaded yet
                        </p>
                    )}
                </div>
            </div>
        </div>
    )
}

export default Document
