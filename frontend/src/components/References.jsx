import React, { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { FileText, BookOpen, X, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const ReferenceModal = ({ isOpen, onClose, documents }) => {
    // Prevent body scroll when modal is open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden'
        } else {
            document.body.style.overflow = 'unset'
        }
        return () => {
            document.body.style.overflow = 'unset'
        }
    }, [isOpen])

    if (!isOpen) return null

    return createPortal(
        <div 
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200"
            onClick={onClose}
        >
            <div 
                className="bg-background w-full max-w-3xl max-h-[85vh] flex flex-col rounded-xl shadow-2xl border animate-in zoom-in-95 duration-200"
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b shrink-0">
                    <div className="flex items-center gap-2">
                        <BookOpen className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                        <h3 className="font-semibold text-lg">Retrieved Documents</h3>
                        <Badge variant="secondary" className="ml-2">
                            {documents.length}
                        </Badge>
                    </div>
                    <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8 rounded-full">
                        <X className="h-4 w-4" />
                    </Button>
                </div>

                {/* Content - Scrollable */}
                <div className="p-4 overflow-y-auto flex-1 space-y-4 custom-scrollbar">
                    {documents.map((doc, index) => (
                        <Card 
                            key={index}
                            className="border-l-4 border-l-blue-500 dark:border-l-blue-400 overflow-hidden transition-all hover:shadow-md"
                        >
                            <CardContent className="p-4">
                                {/* Document header */}
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-2">
                                        <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0">
                                            <FileText className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                                        </div>
                                        <div>
                                            <span className="text-sm font-semibold block">
                                                Document {index + 1}
                                            </span>
                                            {doc.source && (
                                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                                    {doc.source}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    
                                    {/* Score Badge */}
                                    {(doc.score || doc.relevance_score) && (
                                        <Badge variant="outline" className={cn(
                                            "ml-2 font-mono",
                                            (doc.score || doc.relevance_score) > 0.7 ? "bg-green-50 text-green-700 border-green-200" : "bg-blue-50 text-blue-700 border-blue-200"
                                        )}>
                                            {((doc.score || doc.relevance_score) * 100).toFixed(0)}% match
                                        </Badge>
                                    )}
                                </div>

                                {/* Document content */}
                                <div className="bg-muted/30 p-3 rounded-md text-foreground/90 leading-relaxed whitespace-pre-wrap font-mono text-sm">
                                    {doc.content || doc.text || 'No content available'}
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
                
                {/* Footer */}
                <div className="p-3 border-t bg-muted/10 text-center text-xs text-muted-foreground shrink-0">
                    Showing top {documents.length} most relevant results
                </div>
            </div>
        </div>,
        document.body
    )
}

const References = ({ documents = [], className }) => {
    const [isOpen, setIsOpen] = useState(false)

    if (!documents || documents.length === 0) {
        return null
    }

    return (
        <>
            <div className={cn('my-2', className)}>
                <Card 
                    onClick={() => setIsOpen(true)}
                    className='w-full border-blue-200 dark:border-blue-800 cursor-pointer hover:bg-accent/50 transition-all group shadow-sm'
                >
                    <CardContent className='flex items-center justify-between px-3 py-0'>
                        <div className='flex items-center gap-2'>
                            <div className="h-3 w-5 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center group-hover:scale-110 transition-transform">
                                <BookOpen className='h-3 w-3 text-blue-600 dark:text-blue-400' />
                            </div>
                            <div className="flex items-baseline gap-2">
                                <span className='text-sm font-semibold'>References</span>
                                <span className='text-xs text-muted-foreground'>
                                    ({documents.length} source{documents.length > 1 ? 's' : ''})
                                </span>
                            </div>
                        </div>
                        <ExternalLink className='h-3 w-3 text-muted-foreground group-hover:text-blue-500 transition-colors' />
                    </CardContent>
                </Card>
            </div>

            <ReferenceModal 
                isOpen={isOpen} 
                onClose={() => setIsOpen(false)} 
                documents={documents} 
            />
        </>
    )
}

export default References
