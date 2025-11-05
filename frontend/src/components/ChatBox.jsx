import { useAppContext } from '@/context/AppContext'
import React, { useEffect, useState, useRef } from 'react'
import Message from './Message'
import { Bot } from 'lucide-react'
import { PromptInput, PromptInputSubmit, PromptInputTextarea, PromptInputToolbar }
    from './ui/shadcn-io/ai/prompt-input'
import axios from 'axios'
import { askApi } from '@/api/ask'
import { chatApi } from '@/api/chat'
import { toast } from 'sonner'


const ChatBox = () => {
    const containerRef = useRef(null)
    const { selectedChat, setSelectedChat, chats, setChats, user, fetchUser } = useAppContext()
    const [messages, setMessages] = useState([])
    const [prompt, setPrompt] = useState('')
    const [loading, setLoading] = useState(false)


    const handleSubmit = async () => {
        if (!prompt.trim() || loading) return;

        // Store prompt before clearing
        const userPrompt = prompt;
        setPrompt(''); // Clear immediately for better UX
        setLoading(true);

        try {
            const userMessage = { 'role': 'user', 'content': userPrompt, 'created_at': Date.now() };

            // Add user message to UI immediately
            setMessages(prevMessages => [...prevMessages, userMessage]);

            // Update the selectedChat context with new message
            setSelectedChat(prev => ({
                ...prev,
                message_list: [...(prev?.message_list || []), userMessage]
            }));

            // Save to backend
            await chatApi.addMessage(
                user._id, selectedChat._id,
                userMessage
            )

            // Get response after submitting user message
            await handleResponse(userPrompt);

        } catch (error) {
            console.error(`Failed to add new message: ${error}`)
            setLoading(false);
            toast.error('Failed to send message. Please try again.');
        }
    }

    const handleResponse = async (prompt) => {
        try {
            const response = await askApi.askQuestion(prompt)
            const assistantMessage = { 'role': 'assistant', 'content': response, 'created_at': Date.now() };

            setMessages(prevMessages => [...prevMessages, assistantMessage])
            setLoading(false)

            // Update the selectedChat context with new message
            setSelectedChat(prev => ({
                ...prev,
                message_list: [...(prev?.message_list || []), assistantMessage]
            }));

            try {
                await chatApi.addMessage(
                    user._id, selectedChat._id,
                    assistantMessage
                )
                // Refresh user data to sync with database
                await fetchUser(false)
            } catch (error) {
                console.error('Failed to save assistant message:', error);
            }

        } catch (error) {
            console.error(`Failed to generate answer: ${error}`)
            setLoading(false)
            toast.error(`Failed to generate answer: ${error.message || error}`)

            const errorMessage = {
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.',
                created_at: Date.now()
            };
            setMessages(prevMessages => [...prevMessages, errorMessage]);
        }
    }

    useEffect(() => {
        if (selectedChat) {
            setMessages(selectedChat.message_list || [])
        } else {
            setMessages([])
        }
    }, [selectedChat])

    // scroll down to the latest message
    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.scrollTo({
                top: containerRef.current.scrollHeight, behavior: 'smooth'
            })
        }
    }, [messages])


    return (
        <div className='flex-1 flex flex-col justify-between m-5 md:m-10 xl:mx-30 max-md:mt-14 2xl:pr-40'>

            {/* Chat messages */}
            <div ref={containerRef} className='flex-1 mb-5 overflow-y-scroll'>
                {messages.length === 0 && (
                    <div className='h-full flex flex-col items-center justify-center gap-2 text-primary'>
                        <p className='mt-5 text-4xl sm:text-5xl text-center text-gray-400'>
                            Hello @{user?.name || 'Guest'}
                        </p>

                        <p className='mt-5 text-4xl sm:text-5xl text-center text-gray-400'>
                            Type below to ask me
                        </p>
                    </div>
                )}
                {messages.map((message, index) => (
                    <Message key={`${message.created_at}-${index}`} message={message} />
                ))}
                {loading && (
                    <div className='flex items-start gap-2 my-4'>
                        <Bot className='h-6 w-6 mt-1 shrink-0' />
                        <div className='flex flex-col gap-2 p-2 px-4 max-w-2xl bg-primary/5 border border-[#80609F]/30 rounded-md'>
                            <div className='text-sm text-gray-500'>Thinking...</div>
                        </div>
                    </div>
                )}
            </div>

            {/* Prompt input box */}
            <PromptInput
                onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
                className="flex border rounded-xl shadow-sm"
            >
                <PromptInputTextarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSubmit();
                        }
                    }}
                    placeholder='Type your message...'
                    className="flex-row resize-none min-h-11 max-h-32 py-3 px-4"
                />
                <PromptInputToolbar className="flex-row px-2 py-2 justify-end">
                    <PromptInputSubmit
                        disabled={!prompt.trim() || loading}
                        className="h-8 w-8 rounded-md cursor-pointer"
                    />
                </PromptInputToolbar>
            </PromptInput>


        </div>
    )
}

export default ChatBox
