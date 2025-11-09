import React, { useState } from 'react'
import { ChevronDown, ChevronUp, FileText, BookOpen } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const References = ({ documents = [], className }) => {
    const [isExpanded, setIsExpanded] = useState(false)

    if (!documents || documents.length === 0) {
        return null
    }

    return (
        <div className={cn('my-3', className)}>
            <Card className='max-w-2xl border-blue-200 dark:border-blue-800'>
                {/* Header - always visible */}
                <CardContent
                    onClick={() => setIsExpanded(!isExpanded)}
                    className='flex items-center justify-between p-3 cursor-pointer transition-all hover:bg-accent/50'
                >
                    <div className='flex items-center gap-3 max-h-1'>
                        <BookOpen className='h-5 w-5 text-blue-600 dark:text-blue-400' />
                        <div>
                            <div className='text-sm font-semibold flex items-center gap-2'>
                                <span>References</span>
                                <Badge variant='secondary' className='text-xs'>
                                    {documents.length}
                                </Badge>
                            </div>
                            {!isExpanded && (
                                <div className='text-xs text-muted-foreground mt-0.5'>
                                    {documents.length} document{documents.length > 1 ? 's' : ''} retrieved
                                </div>
                            )}
                        </div>
                    </div>
                    {isExpanded ? (
                        <ChevronUp className='h-5 w-5 text-muted-foreground' />
                    ) : (
                        <ChevronDown className='h-5 w-5 text-muted-foreground' />
                    )}
                </CardContent>

                {/* Expanded content */}
                {isExpanded && (
                    <CardContent className='px-4 pb-4 pt-0 space-y-3 border-t bg-accent/10'>
                        {documents.map((doc, index) => (
                            <Card 
                                key={index}
                                className='border-l-4 border-l-blue-500 dark:border-l-blue-400 hover:shadow-md transition-all'
                            >
                                <CardContent className='p-3'>
                                    {/* Document header */}
                                    <div className='flex items-start justify-between mb-2'>
                                        <div className='flex items-center gap-2'>
                                            <FileText className='h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0' />
                                            <span className='text-xs font-semibold text-muted-foreground'>
                                                Document {index + 1}
                                            </span>
                                        </div>
                                        {doc.source && (
                                            <Badge 
                                                variant='outline' 
                                                className='text-[10px] h-5 bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800'
                                            >
                                                {doc.source}
                                            </Badge>
                                        )}
                                    </div>

                                    {/* Document content */}
                                    <div className='text-xs text-foreground/90 leading-relaxed'>
                                        {doc.content || doc.text || 'No content available'}
                                    </div>

                                    {/* Additional metadata if available */}
                                    {(doc.score || doc.relevance_score) && (
                                        <div className='mt-2 pt-2 border-t border-dashed'>
                                            <div className='flex items-center gap-2'>
                                                <span className='text-[10px] text-muted-foreground'>
                                                    Relevance:
                                                </span>
                                                <div className='flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden'>
                                                    <div 
                                                        className='h-full bg-blue-500'
                                                        style={{ 
                                                            width: `${((doc.score || doc.relevance_score) * 100)}%` 
                                                        }}
                                                    />
                                                </div>
                                                <span className='text-[10px] font-medium text-blue-600 dark:text-blue-400'>
                                                    {((doc.score || doc.relevance_score) * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        ))}
                    </CardContent>
                )}
            </Card>
        </div>
    )
}

export default References
