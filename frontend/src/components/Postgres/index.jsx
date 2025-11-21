import React, { useState, useEffect } from "react";
import { useAppContext } from "@/context/AppContext";
import { postgresApi } from "@/api/postgres";
import CsvUploadSection from "./CsvUploadSection";
import TableListSection from "./TableListSection";
import { Database, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

const PostgresPage = () => {
    const { user } = useAppContext();
    const [tables, setTables] = useState([]);
    const [isLoading, setIsLoading] = useState(false);

    const fetchTables = async () => {
        if (!user?._id) return;

        setIsLoading(true);
        try {
            const response = await postgresApi.getUserTables(user._id);
            setTables(response.tables || []);
        } catch (error) {
            console.error("Failed to fetch tables:", error);
            setTables([]);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchTables();
    }, [user?._id]);

    return (
        <div className='flex flex-col w-full p-10 gap-6'>
            {/* Header Section */}
            <div className='flex flex-col gap-2'>
                <div className="flex items-center justify-between">
                    <h2 className='text-2xl font-semibold'>Upload CSV to PostgreSQL</h2>
                    <Button variant="outline" size="sm" onClick={fetchTables} disabled={isLoading}>
                        <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
                        Refresh
                    </Button>
                </div>
                <p className='text-sm text-gray-500'>
                    Upload CSV files to automatically create and populate PostgreSQL tables with intelligent type detection.
                </p>
            </div>

            {/* Upload Section */}
            <CsvUploadSection userId={user?._id} onUploadSuccess={fetchTables} />

            {/* Tables List Section */}
            <div className='flex flex-col gap-4 mt-6'>
                <h3 className='text-xl font-semibold'>Your Tables ({tables.length})</h3>
                <TableListSection
                    tables={tables}
                    isLoading={isLoading}
                    userId={user?._id}
                    onTableDeleted={fetchTables}
                />
            </div>
        </div>
    );
};

export default PostgresPage;
