import React, { useEffect, useState } from 'react'
import { Bot, Search, FileText, Brain, CheckCircle2, Sparkles } from 'lucide-react'
import { Loader } from './ui/shadcn-io/ai/loader'
import { cn } from '@/lib/utils'

const ThinkingIndicator = ({ className }) => {
    const [currentStep, setCurrentStep] = useState(0)
    const [completedSteps, setCompletedSteps] = useState([])
    const [dots, setDots] = useState('')

    const steps = [
        {
            icon: Search,
            label: 'Analyzing your question',
            description: 'Understanding the context and intent',
            duration: 1200
        },
        {
            icon: FileText,
            label: 'Searching knowledge base',
            description: 'Retrieving relevant documents from your files',
            duration: 2000
        },
        {
            icon: Brain,
            label: 'Processing information',
            description: 'Extracting and analyzing relevant context',
            duration: 1500
        },
        {
            icon: Sparkles,
            label: 'Generating response',
            description: 'Crafting a comprehensive answer',
            duration: 1000
        }
    ]

    useEffect(() => {
        // Progress through steps automatically
        const timer = setTimeout(() => {
            if (currentStep < steps.length - 1) {
                setCompletedSteps(prev => [...prev, currentStep])
                setCurrentStep(prev => prev + 1)
            }
        }, steps[currentStep].duration)

        return () => clearTimeout(timer)
    }, [currentStep])

    // Animated dots effect
    useEffect(() => {
        const interval = setInterval(() => {
            setDots(prev => prev.length >= 3 ? '' : prev + '.')
        }, 500)
        return () => clearInterval(interval)
    }, [])

    return (
        <div className={cn('flex items-start gap-3 my-4 animate-in fade-in slide-in-from-bottom-4 duration-300', className)}>
            <Bot className='h-6 w-6 mt-1 shrink-0 text-primary animate-pulse' />
            <div className='flex flex-col gap-3 p-4 max-w-2xl bg-linear-to-r from-primary/5 to-primary/10 border border-primary/30 rounded-lg shadow-sm'>
                {/* Current active step with loader */}
                <div className='flex items-start gap-3'>
                    <Loader size={18} className="text-primary mt-0.5" />
                    <div className='flex-1'>
                        <div className='text-sm font-semibold text-gray-900'>
                            {steps[currentStep].label}{dots}
                        </div>
                        <div className='text-xs text-gray-600 mt-1'>
                            {steps[currentStep].description}
                        </div>
                    </div>
                </div>

                {/* Animated progress bar */}
                <div className='w-full bg-gray-200 rounded-full h-1.5 overflow-hidden'>
                    <div
                        className='bg-primary h-full rounded-full transition-all duration-700 ease-in-out'
                        style={{
                            width: `${((currentStep + 1) / steps.length) * 100}%`
                        }}
                    />
                </div>

                {/* Completed steps - compact badges */}
                {completedSteps.length > 0 && (
                    <div className='flex flex-wrap gap-2'>
                        {completedSteps.map((stepIndex) => {
                            const StepIcon = steps[stepIndex].icon
                            return (
                                <div
                                    key={stepIndex}
                                    className='flex items-center gap-1.5 text-xs text-green-700 bg-green-50 px-2.5 py-1 rounded-full border border-green-200 animate-in fade-in zoom-in duration-200'
                                >
                                    <CheckCircle2 className='h-3 w-3' />
                                    <span className='font-medium'>{steps[stepIndex].label}</span>
                                </div>
                            )
                        })}
                    </div>
                )}

                {/* Visual step indicators */}
                <div className='flex justify-between items-center gap-2 pt-1'>
                    {steps.map((step, index) => {
                        const StepIcon = step.icon
                        const isCompleted = completedSteps.includes(index)
                        const isCurrent = index === currentStep
                        const isUpcoming = index > currentStep

                        return (
                            <div
                                key={index}
                                className='flex flex-col items-center gap-1.5 flex-1'
                            >
                                {/* Icon circle */}
                                <div
                                    className={cn(
                                        'p-2 rounded-full transition-all duration-300 transform',
                                        isCompleted && 'bg-green-100 text-green-600 scale-90',
                                        isCurrent && 'bg-primary/20 text-primary scale-110 ring-2 ring-primary/30',
                                        isUpcoming && 'bg-gray-100 text-gray-400 scale-90 opacity-50'
                                    )}
                                >
                                    {isCompleted ? (
                                        <CheckCircle2 className='h-3.5 w-3.5' />
                                    ) : (
                                        <StepIcon className={cn('h-3.5 w-3.5', isCurrent && 'animate-pulse')} />
                                    )}
                                </div>
                                
                                {/* Step label - only for current step */}
                                {isCurrent && (
                                    <div className='text-[10px] text-center text-gray-500 font-medium leading-tight max-w-[60px]'>
                                        Step {index + 1}/{steps.length}
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>

                {/* Source info hint */}
                {currentStep === 1 && (
                    <div className='text-xs text-gray-500 italic bg-blue-50 px-3 py-1.5 rounded-md border border-blue-100'>
                        💡 Looking through your uploaded documents for relevant information...
                    </div>
                )}
            </div>
        </div>
    )
}

export default ThinkingIndicator
