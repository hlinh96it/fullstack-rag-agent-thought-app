import React, { useState } from "react";
import { useAppContext } from "../context/AppContext";

import { Button } from "./ui/button";
import {
    SquarePlus, Search, Trash2, BadgeDollarSign, FileText, Database
} from "lucide-react";
import { Input } from "./ui/input";
import { Card } from "./ui/card";
import moment from "moment";
import logo_full_dark from '../assets/logo_full_dark.svg'


const Sidebar = () => {
    const { user, navigate, chats, selectedChat, setSelectedChat, createNewChat, deleteChat } = useAppContext();
    const [search, setSearch] = useState("");


    return (
        <div
            className="flex flex-col h-screen min-w-60 max-w-60 p-5 border-r border-[#80609F]/30
                        backdrop-blur-3xl transition-all duration-500 max-md:absolute left-0 z-1"
        >
            {/* Logo */}
            <img src={logo_full_dark} onClick={() => { navigate('/') }} className="cursor-pointer" />

            {/* New chat button */}
            <Button
                className="flex justify-center items-center w-full py-2 mt-10 text-white
                                text-sm cursor-pointer"
                onClick={createNewChat}
            >
                <SquarePlus /> New Chat
            </Button>

            {/* Search history chat */}
            <div className="relative w-full py-2 mt-5">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#6B7280]" />
                <Input
                    type="text" placeholder="Find history chat" className="pl-9 text-black"
                    onChange={(e) => setSearch(e.target.value)} value={search}
                />
            </div>

            {/* Recent chats */}
            <p className="py-4 mt-2">Recent Chats</p>
            <div className="space-y-3 flex-1 overflow-y-auto">
                {chats
                    .filter((chat) => {
                        const searchTerm = search.toLowerCase();
                        if (
                            chat.message_list && chat.message_list.length > 0 &&
                            chat.message_list[0]?.content
                        ) {
                            return chat.message_list[0].content
                                .toLowerCase().includes(searchTerm);
                        }
                        return chat.name?.toLowerCase().includes(searchTerm);
                    })
                    .map((chat) => (
                        <Card
                            key={chat._id || chat.id} onClick={() => {
                                navigate("/");
                                setSelectedChat(chat);
                            }}
                            className="group flex flex-row gap-2 w-full p-3 px-3 py-3 cursor-pointer 
                                       transition-all duration-300 ease-in-out
                                       hover:bg-[#80609F]/10 hover:border-[#80609F]/50 hover:shadow-md
                                       active:scale-[0.98] active:bg-[#80609F]/20
                                       border rounded-lg"
                        >
                            <div className="flex flex-1 flex-col gap-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <p className="text-sm truncate">
                                        {chat.message_list && chat.message_list.length > 0
                                            ? chat.message_list[0].content.slice(0, 32)
                                            : chat.name || "Untitled Chat"}
                                    </p>
                                </div>

                                <p className="text-xs text-gray-500">
                                    {chat.created_at
                                        ? moment(chat.created_at).fromNow()
                                        : "Just now"}
                                </p>
                            </div>
                            <div className="hidden gap-2 group-hover:inline-flex animate-slide-up">
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="shrink-0 transition-colors size-8 text-muted-foreground hover:text-destructive cursor-pointer"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        deleteChat(chat.id || chat._id);
                                        if (chat.id === selectedChat?.id || chat._id === selectedChat?._id) {
                                            setSelectedChat(null)
                                        }
                                    }}
                                >
                                    <Trash2 className="size-4" />
                                </Button>
                            </div>
                        </Card>
                    ))}
            </div>

            {/* Uploaded Documents */}
            <div className="relative mt-auto mb-4 space-y-2">
                <div className="p-0.5 rounded-lg bg-linear-to-r from-purple-300 via-blue-300 to-green-300">
                    <Card
                        onClick={() => navigate("/documents")}
                        className="flex flex-row items-center gap-3 p-4 hover:scale-103 transition-all cursor-pointer bg-white dark:bg-gray-900 rounded-lg"
                    >
                        <FileText className="h-6 w-6 text-[#6B7280] shrink-0" />
                        <div className="flex flex-col gap-1 flex-1 min-w-0">
                            <p className="text-sm font-medium">
                                Document: {user?.doc_list.length || 0}
                            </p>
                            <p className="text-xs text-gray-400">Click to add document</p>
                        </div>
                    </Card>
                </div>

                <div className="p-0.5 rounded-lg bg-linear-to-r from-blue-300 via-indigo-300 to-purple-300">
                    <Card
                        onClick={() => navigate("/postgres")}
                        className="flex flex-row items-center gap-3 p-4 hover:scale-103 transition-all cursor-pointer bg-white dark:bg-gray-900 rounded-lg"
                    >
                        <Database className="h-6 w-6 text-[#6B7280] shrink-0" />
                        <div className="flex flex-col gap-1 flex-1 min-w-0">
                            <p className="text-sm font-medium">
                                PostgreSQL Data
                            </p>
                            <p className="text-xs text-gray-400">Manage CSV tables</p>
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    );
};

export default Sidebar;
