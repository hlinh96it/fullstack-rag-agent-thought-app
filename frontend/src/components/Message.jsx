import { Bot, CircleUserRound } from 'lucide-react'
import React, { useEffect, useMemo } from 'react'
import moment from 'moment'
import Markdown from 'react-markdown'
import Prism from 'prismjs'
import { useAppContext } from '@/context/AppContext'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const Message = ({ message }) => {
    const { user } = useAppContext()
    const isUser = message.role === 'user'

    // Memoize formatted time to avoid unnecessary recalculations
    const formattedTime = useMemo(() => {
        return moment(message.created_at).fromNow()
    }, [message.created_at])

    useEffect(() => {
        // Only highlight if message is from assistant (contains code)
        if (!isUser && message.content) {
            Prism.highlightAll()
        }
    }, [message.content, isUser])

    return (
        <div
            className={cn(
                'group flex items-start gap-4 my-4 w-full',
                isUser ? 'flex-row-reverse justify-start' : 'justify-start'
            )}
        >
            {/* Avatar */}
            <div className={cn(
                'flex items-center justify-center rounded-full shrink-0',
                'size-8 ring-2 ring-border',
                isUser ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'
            )}>
                {isUser ? (
                    <CircleUserRound className='size-5' />
                ) : (
                    <Bot className='size-5' />
                )}
            </div>

            {/* Message Content */}
            <Card className={cn(
                'max-w-2xl shadow-sm',
                isUser
                    ? 'bg-primary/5 border-primary/30'
                    : 'bg-secondary/50 border-secondary'
            )}>
                <CardContent className='flex'>
                    <div className='flex flex-col gap-1'>
                        {/* Message Text */}
                        <div className={cn(
                            'text-sm',
                            !isUser && 'reset-tw prose prose-sm max-w-none'
                        )}>
                            {isUser ? (
                                <p className='whitespace-pre-wrap wrap-break-word'>{message.content}</p>
                            ) : (
                                message.content
                            )}
                        </div>

                        {/* Timestamp and Role Badge */}
                        <div className='flex items-center justify-between gap-2 mt-1'>
                            <span className='text-xs text-muted-foreground'>
                                {formattedTime}
                            </span>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}

export default Message
