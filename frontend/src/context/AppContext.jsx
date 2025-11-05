import { userApi } from "@/api/user";
import { chatApi } from "@/api/chat";
import { createContext, useEffect, useState, useContext, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from 'sonner'
import moment from "moment";


const AppContext = createContext()

// Cache keys
const CACHE_KEYS = {
    USER: 'app_user',
    CHATS: 'app_chats',
    SELECTED_CHAT: 'app_selected_chat'
}

export const AppContextProvider = ({ children }) => {
    const navigate = useNavigate()

    // Initialize state from localStorage
    const [user, setUser] = useState(() => {
        try {
            const cachedUser = localStorage.getItem(CACHE_KEYS.USER)
            return cachedUser ? JSON.parse(cachedUser) : null
        } catch (error) {
            console.error('Error loading cached user:', error)
            return null
        }
    })

    const [chats, setChats] = useState(() => {
        try {
            const cachedChats = localStorage.getItem(CACHE_KEYS.CHATS)
            return cachedChats ? JSON.parse(cachedChats) : []
        } catch (error) {
            console.error('Error loading cached chats:', error)
            return []
        }
    })

    const [selectedChat, setSelectedChat] = useState(() => {
        try {
            const cachedSelectedChat = localStorage.getItem(CACHE_KEYS.SELECTED_CHAT)
            return cachedSelectedChat ? JSON.parse(cachedSelectedChat) : null
        } catch (error) {
            console.error('Error loading cached selected chat:', error)
            return null
        }
    })

    const fetchUser = useCallback(async (showToast = true) => {
        try {
            const response = await userApi.getAllUsers()
            const userData = response.users[0]
            setUser(userData)
            if (showToast) {
                toast.success(`[User loaded]... Hi ${userData.name} `)
            }
        } catch (error) {
            console.error('Failed to fetch user:', error)
            toast.error('Failed to fetch user')
        }
    }, [])

    useEffect(() => {
        // Always fetch fresh data from database on mount
        fetchUser(true)
    }, [fetchUser])

    // Persist user to localStorage
    useEffect(() => {
        try {
            if (user) {
                localStorage.setItem(CACHE_KEYS.USER, JSON.stringify(user))
            } else {
                localStorage.removeItem(CACHE_KEYS.USER)
            }
        } catch (error) {
            console.error('Error caching user:', error)
        }
    }, [user])

    // Persist chats to localStorage
    useEffect(() => {
        try {
            localStorage.setItem(CACHE_KEYS.CHATS, JSON.stringify(chats))
        } catch (error) {
            console.error('Error caching chats:', error)
        }
    }, [chats])

    // Persist selected chat to localStorage
    useEffect(() => {
        try {
            if (selectedChat) {
                localStorage.setItem(CACHE_KEYS.SELECTED_CHAT, JSON.stringify(selectedChat))
            } else {
                localStorage.removeItem(CACHE_KEYS.SELECTED_CHAT)
            }
        } catch (error) {
            console.error('Error caching selected chat:', error)
        }
    }, [selectedChat])

    useEffect(() => {
        if (user) {
            setChats(user.chat_list)

            // If there's a selected chat, update it with fresh data from user.chat_list
            if (selectedChat) {
                const updatedSelectedChat = user.chat_list.find(
                    chat => chat._id === selectedChat._id || chat.id === selectedChat.id
                )
                if (updatedSelectedChat) {
                    setSelectedChat(updatedSelectedChat)
                } else {
                    // Chat was deleted, clear selection
                    setSelectedChat(null)
                }
            }
        } else {
            setChats([])
            setSelectedChat(null)
        }
    }, [user])

    // Create a new chat
    const createNewChat = async () => {
        try {
            const response = await chatApi.createChat(
                user._id, { 'name': `Chat ${user.chat_list.length + 1}`, 'created_at': Date.now() }
            )
            // Refresh user data from database to ensure sync
            await fetchUser(false)
            setSelectedChat(response)
            toast.success('Success', {
                description: `Created new chat successfully`
            })
        } catch (error) {
            toast.error('Failed to create new chat')
            console.error('Failed to create new chat:', error)
        }
    }

    const deleteChat = async (chatId) => {
        try {
            const response = await chatApi.deleteChat(user._id, chatId)
            if (response) {
                // Clear selected chat if it's the one being deleted
                if (selectedChat?._id === chatId || selectedChat?.id === chatId) {
                    setSelectedChat(null)
                }

                // Refresh user data from database to ensure sync
                await fetchUser(false)
                toast.success('Chat deleted successfully')
            }
        } catch (error) {
            console.error('Failed to delete chat:', error)
            toast.error(`Failed to delete chat`)
        }
    }

    // Clear all cached data
    const clearCache = () => {
        try {
            localStorage.removeItem(CACHE_KEYS.USER)
            localStorage.removeItem(CACHE_KEYS.CHATS)
            localStorage.removeItem(CACHE_KEYS.SELECTED_CHAT)
            setUser(null)
            setChats([])
            setSelectedChat(null)
            toast.success('Cache cleared successfully')
        } catch (error) {
            console.error('Error clearing cache:', error)
            toast.error('Failed to clear cache')
        }
    }

    // Update user's document list - memoized to prevent infinite loops
    const updateUserDocList = useCallback((newDocList) => {
        setUser(prevUser => ({
            ...prevUser,
            doc_list: newDocList
        }))
    }, [])

    const value = {
        navigate, user, setUser, fetchUser, chats, setChats, selectedChat, setSelectedChat,
        createNewChat, deleteChat, clearCache, updateUserDocList
    }

    return (
        <AppContext.Provider value={value}>
            {children}
        </AppContext.Provider>
    )
}

export const useAppContext = () => useContext(AppContext)
