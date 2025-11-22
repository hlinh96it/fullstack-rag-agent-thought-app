import React, { useState, useEffect } from "react";
import { useAppContext } from "@/context/AppContext";
import { postgresApi } from "@/api/postgres";
import CsvUploadSection from "./CsvUploadSection";
import TableListSection from "./TableListSection";
import { Database, RefreshCw, Plus, Loader2, RefreshCcw, Trash2, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
    const [manageDbDialogOpen, setManageDbDialogOpen] = useState(false);
    const [newDatabaseName, setNewDatabaseName] = useState("");
    const [isCreatingDb, setIsCreatingDb] = useState(false);
    const [isDeletingDb, setIsDeletingDb] = useState(null);

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
            await fetchDatabases();
        } catch (error) {
            console.error("Failed to create database:", error);
            toast.error(error.message || "Failed to create database");
        } finally {
            setIsCreatingDb(false);
        }
    };

    const handleDeleteDatabase = async (databaseName) => {
        if (!user?._id) {
            toast.error("User not found");
            return;
        }

        if (!confirm(`Are you sure you want to delete database '${databaseName}'? This action cannot be undone.`)) {
            return;
        }

        setIsDeletingDb(databaseName);
        try {
            await postgresApi.deleteDatabase(user._id, databaseName);
            toast.success(`Database '${databaseName}' deleted successfully!`);
            await fetchDatabases();
        } catch (error) {
            console.error("Failed to delete database:", error);
            toast.error(error.message || "Failed to delete database");
        } finally {
            setIsDeletingDb(null);
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
                        <Button variant="outline" size="sm" onClick={() => setManageDbDialogOpen(true)}>
                            <Settings className="h-4 w-4 mr-2" />
                            Manage Databases
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

            {/* Manage Databases Dialog */}
            <Dialog open={manageDbDialogOpen} onOpenChange={setManageDbDialogOpen}>
                <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Settings className="h-5 w-5 text-blue-500" />
                            Manage Databases
                        </DialogTitle>
                        <DialogDescription>
                            View all your databases, check their information, and manage them.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 mt-4">
                        {/* Add New Database Section */}
                        <Card className="border-dashed">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm font-medium">Create New Database</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex gap-2">
                                    <Input
                                        value={newDatabaseName}
                                        onChange={(e) => setNewDatabaseName(e.target.value)}
                                        placeholder="Enter database name..."
                                        disabled={isCreatingDb}
                                        onKeyDown={(e) => {
                                            if (e.key === "Enter" && !isCreatingDb) {
                                                handleCreateDatabase();
                                            }
                                        }}
                                        className="flex-1"
                                    />
                                    <Button
                                        onClick={handleCreateDatabase}
                                        disabled={isCreatingDb || !newDatabaseName.trim()}
                                        size="sm"
                                    >
                                        {isCreatingDb ? (
                                            <>
                                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                Creating...
                                            </>
                                        ) : (
                                            <>
                                                <Plus className="mr-2 h-4 w-4" />
                                                Create
                                            </>
                                        )}
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Database List */}
                        <div className="space-y-3">
                            <h4 className="text-sm font-semibold text-gray-700">
                                Your Databases ({databases.length})
                            </h4>

                            {databases.length === 0 ? (
                                <Card>
                                    <CardContent className="pt-6 text-center text-gray-500">
                                        <Database className="h-12 w-12 mx-auto mb-2 opacity-50" />
                                        <p>No databases found</p>
                                        <p className="text-xs mt-1">Create a new database to get started</p>
                                    </CardContent>
                                </Card>
                            ) : (
                                <div className="grid gap-3 md:grid-cols-2">
                                    {databases.map((db) => (
                                        <Card key={db.database_name} className="relative">
                                            <CardHeader className="pb-3">
                                                <div className="flex items-start justify-between">
                                                    <div className="flex items-center gap-2">
                                                        <Database className="h-4 w-4 text-blue-500" />
                                                        <CardTitle className="text-base">{db.database_name}</CardTitle>
                                                    </div>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => handleDeleteDatabase(db.database_name)}
                                                        disabled={isDeletingDb === db.database_name}
                                                        className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                                                    >
                                                        {isDeletingDb === db.database_name ? (
                                                            <Loader2 className="h-4 w-4 animate-spin" />
                                                        ) : (
                                                            <Trash2 className="h-4 w-4" />
                                                        )}
                                                    </Button>
                                                </div>
                                                <CardDescription className="text-xs">
                                                    {db.table_list?.length || 0} table(s)
                                                </CardDescription>
                                            </CardHeader>
                                            <CardContent className="pt-0">
                                                <div className="space-y-2 text-xs text-gray-600">
                                                    {db.table_list && db.table_list.length > 0 ? (
                                                        <div>
                                                            <p className="font-medium mb-1">Tables:</p>
                                                            <ul className="list-disc list-inside space-y-0.5 max-h-20 overflow-y-auto">
                                                                {db.table_list.map((table) => (
                                                                    <li key={table.table_name} className="text-gray-500">
                                                                        {table.table_name}
                                                                        <span className="text-gray-400 ml-1">
                                                                            ({table.row_count || 0} rows)
                                                                        </span>
                                                                    </li>
                                                                ))}
                                                            </ul>
                                                        </div>
                                                    ) : (
                                                        <p className="text-gray-400 italic">No tables in this database</p>
                                                    )}
                                                </div>
                                            </CardContent>
                                        </Card>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="flex justify-end pt-4 border-t">
                            <Button
                                variant="outline"
                                onClick={() => setManageDbDialogOpen(false)}
                            >
                                Close
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default PostgresPage;
