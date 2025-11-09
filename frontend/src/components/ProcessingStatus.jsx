import React, { useState, useEffect } from 'react'
import { Bot, ChevronDown, ChevronUp, FileText, CheckCircle2, Clock, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

// Helper function to format step names
const formatStepName = (stepName) => {
    if (!stepName) return 'Processing';
    return stepName
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

const ProcessingStatus = ({ 
    processingSteps = [], 
    retrievedDocuments = [], 
    isComplete = false,
    className 
}) => {
    const [isExpanded, setIsExpanded] = useState(true) 
    const [currentStepIndex, setCurrentStepIndex] = useState(0)

    useEffect(() => {
        // Update current step index based on processing steps
        if (processingSteps.length > 0) {
            const inProgressIndex = processingSteps.findIndex(step => step.status === 'in_progress')
            if (inProgressIndex !== -1) {
                setCurrentStepIndex(inProgressIndex)
            } else {
                setCurrentStepIndex(Math.max(0, processingSteps.length - 1))
            }
        }
    }, [processingSteps])

    // Auto-collapse when complete
    useEffect(() => {
        if (isComplete && processingSteps.length > 0) {
            const timer = setTimeout(() => {
                setIsExpanded(false)
            }, 2000) // Collapse after 2 seconds
            return () => clearTimeout(timer)
        }
    }, [isComplete, processingSteps.length])

    const getStepIcon = (step) => {
        if (step.status === 'completed') {
            return <CheckCircle2 className='h-4 w-4 text-green-600' />
        } else if (step.status === 'in_progress') {
            return <Loader2 className='h-4 w-4 text-primary animate-spin' />
        } else {
            return <Clock className='h-4 w-4 text-gray-400' />
        }
    }

    const completedSteps = processingSteps.filter(s => s.status === 'completed').length
    const totalSteps = processingSteps.length || 1 // Avoid division by zero

    // Show loading state if no steps yet
    if (processingSteps.length === 0) {
        return (
            <div className={cn('flex items-start gap-3 my-4', className)}>
                <Bot className='h-6 w-6 mt-1 shrink-0 text-primary animate-pulse' />
                <Card className='flex-1'>
                    <CardContent className='flex items-center gap-3 p-3'>
                        <Loader2 className='h-5 w-5 text-primary animate-spin' />
                        <span className='text-sm font-semibold'>Starting processing...</span>
                    </CardContent>
                </Card>
            </div>
        )
    }

    return (
        <div className={cn('flex items-start gap-3 my-4 transition-all duration-300', className)}>
            <Bot className={cn(
                'h-6 w-6 mt-1 shrink-0 transition-all',
                isComplete ? 'text-green-600' : 'text-primary animate-pulse'
            )} />
            
            <Card className='flex-1 max-w-2xl'>
                {/* Header - always visible */}
                <CardContent
                    onClick={() => setIsExpanded(!isExpanded)}
                    className={cn(
                        'flex items-center justify-between p-3 cursor-pointer transition-all hover:bg-accent/50',
                        isExpanded && 'border-b'
                    )}
                >
                    <div className='flex items-center gap-3 flex-1'>
                        {isComplete ? (
                            <CheckCircle2 className='h-5 w-5 text-green-600' />
                        ) : (
                            <Loader2 className='h-5 w-5 text-primary animate-spin' />
                        )}
                        <div className='flex-1'>
                            <div className='text-sm font-semibold'>
                                {isComplete 
                                    ? '✓ Processing Complete' 
                                    : formatStepName(processingSteps[currentStepIndex]?.step_name) || 'Processing...'}
                            </div>
                            {!isExpanded && (
                                <div className='text-xs text-muted-foreground mt-0.5'>
                                    {isComplete 
                                        ? `${totalSteps} steps completed • ${retrievedDocuments.length} documents found`
                                        : `Step ${completedSteps + 1}/${totalSteps}`}
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
                    <CardContent className='p-4 space-y-4 bg-accent/20'>
                        {/* Progress bar */}
                        <div className='space-y-2'>
                            <div className='flex justify-between text-xs text-muted-foreground'>
                                <span>Progress</span>
                                <span>{completedSteps}/{totalSteps} steps</span>
                            </div>
                            <Progress 
                                value={(completedSteps / totalSteps) * 100}
                                className={cn(
                                    'h-2',
                                    isComplete && '[&>div]:bg-green-600'
                                )}
                            />
                        </div>

                        {/* Processing steps */}
                        <div className='space-y-2'>
                            <div className='text-xs font-semibold text-muted-foreground uppercase tracking-wide'>
                                Processing Steps
                            </div>
                            {processingSteps.map((step, index) => (
                                <div
                                    key={index}
                                    className={cn(
                                        'flex items-start gap-2 p-2 rounded-md transition-all',
                                        step.status === 'completed' && 'bg-green-50 dark:bg-green-950/20',
                                        step.status === 'in_progress' && 'bg-blue-50 dark:bg-blue-950/20 ring-1 ring-blue-200 dark:ring-blue-800'
                                    )}
                                >
                                    {getStepIcon(step)}
                                    <div className='flex-1 min-w-0'>
                                        <div className='text-xs font-medium'>
                                            {formatStepName(step.step_name)}
                                        </div>
                                        {step.details && (
                                            <div className='text-xs text-muted-foreground mt-0.5'>
                                                {step.details}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Retrieved documents */}
                        {retrievedDocuments.length > 0 && (
                            <div className='space-y-2'>
                                <div className='flex items-center justify-between'>
                                    <div className='text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-1.5'>
                                        <FileText className='h-3.5 w-3.5' />
                                        Retrieved Documents ({retrievedDocuments.length})
                                    </div>
                                </div>
                                <div className='space-y-2 max-h-60 overflow-y-auto'>
                                    {retrievedDocuments.map((doc, index) => (
                                        <Card key={index} className='p-3'>
                                            <div className='flex items-start justify-between mb-1'>
                                                <span className='text-xs font-medium'>
                                                    Document {index + 1}
                                                </span>
                                                {doc.source && (
                                                    <Badge variant='secondary' className='text-[10px] h-5'>
                                                        {doc.source}
                                                    </Badge>
                                                )}
                                            </div>
                                            <div className='text-xs text-muted-foreground line-clamp-3'>
                                                {doc.content}
                                            </div>
                                        </Card>
                                    ))}
                                </div>
                            </div>
                        )}
                    </CardContent>
                )}
            </Card>
        </div>
    )
}

export default ProcessingStatus
