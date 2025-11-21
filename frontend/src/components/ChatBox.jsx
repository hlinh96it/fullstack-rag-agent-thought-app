import { useAppContext } from "@/context/AppContext";
import React, { useEffect, useState, useRef } from "react";
import Message from "./Message";
import ProcessingStatus from "./ProcessingStatus";
import {
    PromptInput,
    PromptInputSubmit,
    PromptInputTextarea,
    PromptInputToolbar,
} from "./ui/shadcn-io/ai/prompt-input";

import { askApi } from "@/api/ask";
import { chatApi } from "@/api/chat";
import { toast } from "sonner";

const ChatBox = () => {
    const containerRef = useRef(null);
    const { selectedChat, setSelectedChat, chats, setChats, user, fetchUser } =
        useAppContext();
    const [messages, setMessages] = useState([]);
    const [prompt, setPrompt] = useState("");
    const [loading, setLoading] = useState(false);
    const [processingData, setProcessingData] = useState(null); // Stores { steps, documents, isComplete }

    const handleSubmit = async () => {
        if (!prompt.trim() || loading) return;

        // Store prompt before clearing
        const userPrompt = prompt;
        setPrompt(""); // Clear immediately for better UX
        setLoading(true);

        try {
            const userMessage = {
                role: "user",
                content: userPrompt,
                created_at: Date.now(),
            };

            // Add user message to UI immediately
            setMessages((prevMessages) => [...prevMessages, userMessage]);

            // Update the selectedChat context with new message
            setSelectedChat((prev) => ({
                ...prev,
                message_list: [...(prev?.message_list || []), userMessage],
            }));

            // Save to backend
            await chatApi.addMessage(user._id, selectedChat._id, userMessage);

            // Get response after submitting user message
            await handleResponse(userPrompt);
        } catch (error) {
            console.error(`Failed to add new message: ${error}`);
            setLoading(false);
            toast.error("Failed to send message. Please try again.");
        }
    };

    const handleResponse = async (prompt) => {
        // Track when we started
        const startTime = Date.now();

        try {
            // Initialize processing data with estimated steps
            // These will be replaced with real data when response comes back
            const estimatedSteps = [
                {
                    step_name: "analyze_question",
                    status: "in_progress",
                    timestamp: startTime / 1000,
                    details: "Analyzing your question...",
                },
            ];

            setProcessingData({
                steps: estimatedSteps,
                documents: [],
                isComplete: false,
            });

            // Simulate progress updates while waiting for response
            const progressInterval = setInterval(() => {
                setProcessingData((prev) => {
                    if (!prev || prev.isComplete) return prev;

                    const elapsed = (Date.now() - startTime) / 1000;
                    const newSteps = [...prev.steps];

                    // Add steps based on elapsed time
                    if (elapsed > 1 && newSteps.length === 1) {
                        newSteps[0].status = "completed";
                        newSteps.push({
                            step_name: "search_documents",
                            status: "in_progress",
                            timestamp: Date.now() / 1000,
                            details: "Searching through your documents...",
                        });
                    } else if (elapsed > 3 && newSteps.length === 2) {
                        newSteps[1].status = "completed";
                        newSteps.push({
                            step_name: "grade_documents",
                            status: "in_progress",
                            timestamp: Date.now() / 1000,
                            details: "Evaluating document relevance...",
                        });
                    } else if (elapsed > 4 && newSteps.length === 3) {
                        newSteps[2].status = "completed";
                        newSteps.push({
                            step_name: "generate_answer",
                            status: "in_progress",
                            timestamp: Date.now() / 1000,
                            details: "Generating your answer...",
                        });
                    }

                    return { ...prev, steps: newSteps };
                });
            }, 500);

            // Prepare chat history (last 5 messages for context, excluding system messages)
            const recentMessages = messages
                .slice(-10) // Get last 10 messages for context
                .filter((msg) => msg.role !== "system")
                .map((msg) => ({
                    role: msg.role,
                    content: msg.content,
                }));

            const response = await askApi.askQuestion(prompt, recentMessages);

            // Stop the progress simulation
            clearInterval(progressInterval);

            // Extract answer and metadata
            const answer = response?.answer || response;
            const processingSteps = response?.processing_steps || [];
            const retrievedDocuments = response?.retrieved_documents || [];

            // Update processing data with REAL information from backend
            // If backend didn't return steps, use our estimated ones
            const finalSteps =
                processingSteps.length > 0
                    ? processingSteps
                    : [
                        {
                            step_name: "analyze_question",
                            status: "completed",
                            timestamp: startTime / 1000,
                            details: "Question analyzed",
                        },
                        {
                            step_name: "search_documents",
                            status: "completed",
                            timestamp: (startTime + 1500) / 1000,
                            details: "Documents searched",
                        },
                        {
                            step_name: "grade_documents",
                            status: "completed",
                            timestamp: (startTime + 3000) / 1000,
                            details: "Documents evaluated",
                        },
                        {
                            step_name: "generate_answer",
                            status: "completed",
                            timestamp: Date.now() / 1000,
                            details: "Answer generated",
                        },
                    ];

            setProcessingData({
                steps: finalSteps,
                documents: retrievedDocuments,
                isComplete: true,
            });

            const assistantMessage = {
                role: "assistant",
                content: answer,
                created_at: Date.now(),
                processing_steps: finalSteps,
                retrieved_documents: retrievedDocuments,
            };

            setMessages((prevMessages) => [...prevMessages, assistantMessage]);
            setLoading(false);

            // Update the selectedChat context with new message
            setSelectedChat((prev) => ({
                ...prev,
                message_list: [...(prev?.message_list || []), assistantMessage],
            }));

            // Also update the chats list to keep it in sync
            setChats((prevChats) =>
                prevChats.map((chat) =>
                    chat._id === selectedChat._id
                        ? { ...chat, message_list: [...(chat.message_list || []), assistantMessage] }
                        : chat
                )
            );

            try {
                await chatApi.addMessage(user._id, selectedChat._id, assistantMessage);
            } catch (error) {
                console.error("Failed to save assistant message:", error);
            }
        } catch (error) {
            console.error(`Failed to generate answer: ${error}`);
            setLoading(false);
            setProcessingData(null);

            // Extract detailed error message
            let errorMessage = "Sorry, I encountered an error. Please try again.";
            if (error?.message) {
                errorMessage = error.message;
            } else if (typeof error === "string") {
                errorMessage = error;
            }

            // Show error toast with specific message
            toast.error(errorMessage);

            const errorMessageObj = {
                role: "assistant",
                content: errorMessage,
                created_at: Date.now(),
            };
            setMessages((prevMessages) => [...prevMessages, errorMessageObj]);
        }
    };

    useEffect(() => {
        if (selectedChat) {
            setMessages(selectedChat.message_list || []);
        } else {
            setMessages([]);
        }
    }, [selectedChat]);

    // scroll down to the latest message
    useEffect(() => {
        if (containerRef.current) {
            containerRef.current.scrollTo({
                top: containerRef.current.scrollHeight,
                behavior: "smooth",
            });
        }
    }, [messages]);

    return (
        <div className="flex-1 flex flex-col justify-between m-5 md:m-10 xl:mx-30 max-md:mt-14 2xl:pr-40">
            {/* Chat messages */}
            <div ref={containerRef} className="flex-1 mb-5 overflow-y-scroll">
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center gap-2 text-primary">
                        <p className="mt-5 text-4xl sm:text-5xl text-center text-gray-400">
                            Hello @{user?.name || "Guest"}
                        </p>

                        <p className="mt-5 text-4xl sm:text-5xl text-center text-gray-400">
                            Type below to ask me
                        </p>
                    </div>
                )}
                {messages.map((message, index) => {
                    return (
                        <React.Fragment key={`${message.created_at}-${index}`}>
                            {message.role === "assistant" && (
                                <>
                                    {/* Show processing status if this is the last assistant message and we have processing data */}
                                    {index === messages.length - 1 && processingData && (
                                        <ProcessingStatus
                                            processingSteps={processingData.steps}
                                            retrievedDocuments={processingData.documents}
                                            isComplete={processingData.isComplete}
                                        />
                                    )}
                                </>
                            )}
                            <Message
                                message={message}
                                messages={messages}
                                index={index}
                                processingData={processingData}
                            />
                        </React.Fragment>
                    );
                })}

                {/* Show processing status while loading (before message is added) */}
                {loading &&
                    processingData &&
                    messages[messages.length - 1]?.role !== "assistant" && (
                        <ProcessingStatus
                            processingSteps={processingData.steps}
                            retrievedDocuments={processingData.documents}
                            isComplete={processingData.isComplete}
                        />
                    )}
            </div>

            {/* Prompt input box */}
            <PromptInput
                onSubmit={(e) => {
                    e.preventDefault();
                    handleSubmit();
                }}
                className="flex border rounded-xl shadow-sm"
            >
                <PromptInputTextarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            handleSubmit();
                        }
                    }}
                    placeholder="Type your message..."
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
    );
};

export default ChatBox;
