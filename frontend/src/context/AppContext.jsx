import { userApi } from "@/api/user";
import { chatApi } from "@/api/chat";
import { createContext, useEffect, useState, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from 'sonner'
import moment from "moment";


const AppContext = createContext()

export const AppContextProvider = ({ children }) => {
    const navigate = useNavigate()
    const [user, setUser] = useState(null)
    const [chats, setChats] = useState([])  // all chat of specific user
    const [selectedChat, setSelectedChat] = useState(null)  // select specific chat

    const fetchUser = async () => {
        try {

            const response = await userApi.getAllUsers()
            const userData = response.users[0]
            setUser(userData)
            toast.success(`[User loaded]... Hi ${userData.name} `)
        } catch (error) {
            toast.error('Failed to fetch user:', error)
        }
    }

    useEffect(() => {
        // Load user from cache or fetch
        fetchUser()
    }, [])

    useEffect(() => {
        if (user) {
            setChats(user.chat_list)
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
            const updatedChats = [response, ...chats]
            setChats(updatedChats)
            setSelectedChat(response.message_list || [])
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
                // Update local state by removing the deleted chat
                const updatedChats = chats.filter(chat => chat._id !== chatId)
                setChats(updatedChats)

                // Clear selected chat if it's the one being deleted
                if (selectedChat?._id === chatId) {
                    setSelectedChat(null)
                }

                toast.success('Chat deleted successfully')
            }
        } catch (error) {
            console.error('Failed to delete chat:', error)
            toast.error(`Failed to delete chat`)
        }
    }

    const value = {
        navigate, user, setUser, fetchUser, chats, setChats, selectedChat, setSelectedChat,
        createNewChat, deleteChat
    }

    return (
        <AppContext.Provider value={value}>
            {children}
        </AppContext.Provider>
    )
}

export const useAppContext = () => useContext(AppContext)
