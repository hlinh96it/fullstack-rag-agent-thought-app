import React from 'react'
import { Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'

import Sidebar from './components/Sidebar'
import ChatBox from './components/ChatBox';
import './assets/prism.css'
import Document from './components/Document';
import PostgresPage from './components/Postgres';


const App = () => {
    return (
        <>
            <Toaster position="top-right" richColors />
            <div className='flex h-screen w-screen'>

                <Sidebar />
                <Routes>
                    <Route path='/' element={<ChatBox />} />
                    <Route path='/documents' element={<Document />} />
                    <Route path='/postgres' element={<PostgresPage />} />
                </Routes>

            </div>
        </>
    )
}

export default App
