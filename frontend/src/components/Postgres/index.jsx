import React, { useState, useEffect } from "react";
import { useAppContext } from "@/context/AppContext";
import { postgresApi } from "@/api/postgres";
import CsvUploadSection from "./CsvUploadSection";
import TableListSection from "./TableListSection";
import { Database, RefreshCw, Plus, Loader2, RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";

const PostgresPage = () => {
    const { user } = useAppContext();
    const [databases, setDatabases] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isSyncing, setIsSyncing] = useState(false);
    const [activeTab, setActiveTab] = useState("all");
    const [createDbDialogOpen, setCreateDbDialogOpen] = useState(false);
    const [newDatabaseName, setNewDatabaseName] = useState("");
    const [isCreatingDb, setIsCreatingDb] = useState(false);

    const fetchDatabases = async () => {
        if (!user?._id) return;

        try {
            const response = await postgresApi.listDatabases(user._id);
            setDatabases(response.databases || []);
        } catch (error) {
            console.error("Failed to fetch databases:", error);
            setDatabases([]);
        }
    };

    const handleRefresh = async () => {
        await fetchDatabases();
    };

    const handleSync = async () => {
        if (!user?._id) return;

        setIsSyncing(true);
        try {
            const response = await postgresApi.syncDatabases(user._id);

            // Show sync summary
            const summary = response.summary;
            const changes = [
                ...summary.databases_added.map(db => `+ Database: ${db}`),
                ...summary.databases_removed.map(db => `- Database: ${db}`),
                ...summary.tables_added.map(t => `+ Table: ${t}`),
                ...summary.tables_removed.map(t => `- Table: ${t}`),
                ...summary.tables_updated.map(t => `↻ Updated: ${t}`),
            ];

            if (changes.length > 0) {
                toast.success(`Sync completed! ${changes.length} change(s) detected.`, {
                    description: changes.slice(0, 5).join('\n') + (changes.length > 5 ? `\n... and ${changes.length - 5} more` : ''),
                });
            } else {
                toast.success("Everything is already in sync!");
            }

            await fetchDatabases();
        } catch (error) {
            console.error("Failed to sync:", error);
            toast.error(error.message || "Failed to sync databases");
        } finally {
            setIsSyncing(false);
        }
    };

    const handleCreateDatabase = async () => {
        if (!newDatabaseName.trim()) {
            toast.error("Please enter a database name");
            return;
        }

        if (!user?._id) {
            toast.error("User not found");
            return;
        }

        setIsCreatingDb(true);
        try {
            await postgresApi.createDatabase(user._id, newDatabaseName.trim());
            toast.success(`Database '${newDatabaseName}' created successfully!`);
            setNewDatabaseName("");
            setCreateDbDialogOpen(false);
            await fetchDatabases();
        } catch (error) {
            console.error("Failed to create database:", error);
            toast.error(error.message || "Failed to create database");
        } finally {
            setIsCreatingDb(false);
        }
    };

    useEffect(() => {
        if (user?._id) {
            fetchDatabases();
        }
    }, [user?._id]);

    // Extract all tables from all databases
    const allTables = databases.flatMap(db =>
        (db.table_list || []).map(table => ({
            ...table,
            database_name: db.database_name
        }))
    );

    // Group tables by database
    const tablesByDatabase = databases.reduce((acc, db) => {
        if (db.table_list && db.table_list.length > 0) {
            acc[db.database_name] = db.table_list.map(table => ({
                ...table,
                database_name: db.database_name
            }));
        }
        return acc;
    }, {});

    const databaseNames = Object.keys(tablesByDatabase).sort();

    return (
        <div className='flex flex-col w-full p-10 gap-6'>
            {/* Header Section */}
            <div className='flex flex-col gap-2'>
                <div className="flex items-center justify-between">
                    <h2 className='text-2xl font-semibold'>Upload CSV to PostgreSQL</h2>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => setCreateDbDialogOpen(true)}>
                            <Plus className="h-4 w-4 mr-2" />
                            New Database
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={handleSync}
                            disabled={isSyncing || !user?._id}
                            title="Sync with PostgreSQL"
                        >
                            <RefreshCcw className={`h-4 w-4 mr-2 ${isSyncing ? "animate-spin" : ""}`} />
                            Sync
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoading}>
                            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
                            Refresh
                        </Button>
                    </div>
                </div>
                <p className='text-sm text-gray-500'>
                    Upload CSV files to automatically create and populate PostgreSQL tables with intelligent type detection.
                </p>
            </div>

            {/* Upload Section */}
            <CsvUploadSection userId={user?._id} onUploadSuccess={handleRefresh} databases={databases} />

            {/* Tables List Section with Tabs */}
            <div className='flex flex-col gap-4 mt-6'>
                <h3 className='text-xl font-semibold'>Your Tables ({allTables.length})</h3>

                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="mb-4">
                        <TabsTrigger value="all">
                            All Tables ({allTables.length})
                        </TabsTrigger>
                        {databaseNames.map((dbName) => (
                            <TabsTrigger key={dbName} value={dbName}>
                                <Database className="h-3 w-3 mr-1" />
                                {dbName} ({tablesByDatabase[dbName].length})
                            </TabsTrigger>
                        ))}
                    </TabsList>

                    <TabsContent value="all">
                        <TableListSection
                            tables={allTables}
                            isLoading={isLoading}
                            userId={user?._id}
                            onTableDeleted={handleRefresh}
                        />
                    </TabsContent>

                    {databaseNames.map((dbName) => (
                        <TabsContent key={dbName} value={dbName}>
                            <TableListSection
                                tables={tablesByDatabase[dbName]}
                                isLoading={isLoading}
                                userId={user?._id}
                                onTableDeleted={handleRefresh}
                            />
                        </TabsContent>
                    ))}
                </Tabs>
            </div>

            {/* Create Database Dialog */}
            <Dialog open={createDbDialogOpen} onOpenChange={setCreateDbDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Database className="h-5 w-5 text-blue-500" />
                            Create New Database
                        </DialogTitle>
                        <DialogDescription>
                            Enter a name for your new PostgreSQL database. The name will be sanitized automatically.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 mt-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Database Name</label>
                            <Input
                                value={newDatabaseName}
                                onChange={(e) => setNewDatabaseName(e.target.value)}
                                placeholder="my_database"
                                disabled={isCreatingDb}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && !isCreatingDb) {
                                        handleCreateDatabase();
                                    }
                                }}
                            />
                        </div>

                        <div className="flex justify-end gap-2">
                            <Button
                                variant="outline"
                                onClick={() => {
                                    setCreateDbDialogOpen(false);
                                    setNewDatabaseName("");
                                }}
                                disabled={isCreatingDb}
                            >
                                Cancel
                            </Button>
                            <Button
                                onClick={handleCreateDatabase}
                                disabled={isCreatingDb || !newDatabaseName.trim()}
                            >
                                {isCreatingDb ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Creating...
                                    </>
                                ) : (
                                    <>
                                        <Plus className="mr-2 h-4 w-4" />
                                        Create Database
                                    </>
                                )}
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default PostgresPage;
