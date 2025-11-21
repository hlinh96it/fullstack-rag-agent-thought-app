import React, { useState } from "react";
import { Table as TableIcon, Database, Calendar, FileText, Layers, Loader2, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { postgresApi } from "@/api/postgres";
import { toast } from "sonner";
import moment from "moment";

const TableListSection = ({ tables, isLoading, onTableDeleted, userId }) => {
    const [selectedTable, setSelectedTable] = useState(null);
    const [tableData, setTableData] = useState(null);
    const [loadingData, setLoadingData] = useState(false);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [deletingTable, setDeletingTable] = useState(null);

    const handleTableClick = async (table) => {
        setSelectedTable(table);
        setDialogOpen(true);
        setLoadingData(true);
        setTableData(null);

        try {
            const response = await postgresApi.getTableData(table.table_name);
            setTableData(response);
        } catch (error) {
            console.error("Failed to fetch table data:", error);
            toast.error(error.message || "Failed to load table data");
        } finally {
            setLoadingData(false);
        }
    };

    const handleDeleteTable = async (e, table) => {
        e.stopPropagation(); // Prevent card click

        if (!confirm(`Are you sure you want to delete table "${table.table_name}"? This action cannot be undone.`)) {
            return;
        }

        setDeletingTable(table.table_name);

        try {
            await postgresApi.deleteTable(userId, table.table_name);
            toast.success(`Table "${table.table_name}" deleted successfully`);

            if (onTableDeleted) {
                onTableDeleted();
            }
        } catch (error) {
            console.error("Failed to delete table:", error);
            toast.error(error.message || "Failed to delete table");
        } finally {
            setDeletingTable(null);
        }
    };

    if (isLoading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                    <Card key={i} className="animate-pulse">
                        <CardHeader className="h-24 bg-gray-100 dark:bg-gray-800 rounded-t-lg" />
                        <CardContent className="h-32" />
                    </Card>
                ))}
            </div>
        );
    }

    if (!tables || tables.length === 0) {
        return (
            <div className="text-center py-12 border rounded-lg bg-gray-50/50 dark:bg-gray-900/50">
                <Database className="h-12 w-12 mx-auto text-gray-400 mb-3" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No tables found</h3>
                <p className="text-gray-500 dark:text-gray-400">Upload a CSV file to create your first table</p>
            </div>
        );
    }

    return (
        <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {tables.map((table, index) => (
                    <Card
                        key={index}
                        className="hover:shadow-md transition-shadow border-l-4 border-l-blue-500 cursor-pointer group"
                        onClick={() => handleTableClick(table)}
                    >
                        <CardHeader className="pb-2">
                            <div className="flex justify-between items-start gap-2">
                                <CardTitle className="text-lg font-bold flex items-center gap-2 break-words flex-1">
                                    <TableIcon className="h-5 w-5 text-blue-500 flex-shrink-0" />
                                    <span className="break-all">{table.table_name}</span>
                                </CardTitle>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 text-muted-foreground hover:text-destructive"
                                    onClick={(e) => handleDeleteTable(e, table)}
                                    disabled={deletingTable === table.table_name}
                                >
                                    {deletingTable === table.table_name ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <Trash2 className="h-4 w-4" />
                                    )}
                                </Button>
                            </div>
                            <p className="text-xs text-muted-foreground flex items-center gap-1 break-words">
                                <FileText className="h-3 w-3 flex-shrink-0" />
                                <span className="break-all">Original: {table.original_filename}</span>
                            </p>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3">
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-muted-foreground flex items-center gap-1">
                                        <Layers className="h-3 w-3" /> Rows:
                                    </span>
                                    <span className="font-medium">{table.row_count.toLocaleString()}</span>
                                </div>
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-muted-foreground">Columns:</span>
                                    <span className="font-medium">{table.column_count}</span>
                                </div>

                                <div className="pt-2 border-t mt-2">
                                    <p className="text-xs text-muted-foreground mb-2">Columns:</p>
                                    <div className="flex flex-wrap gap-1">
                                        {table.columns.slice(0, 5).map((col, i) => (
                                            <Badge key={i} variant="secondary" className="text-[10px]">
                                                {col}
                                            </Badge>
                                        ))}
                                        {table.columns.length > 5 && (
                                            <Badge variant="outline" className="text-[10px]">
                                                +{table.columns.length - 5} more
                                            </Badge>
                                        )}
                                    </div>
                                </div>

                                <div className="pt-2 flex items-center gap-1 text-xs text-muted-foreground">
                                    <Calendar className="h-3 w-3" />
                                    {table.created_at
                                        ? moment.unix(table.created_at).format("MMM D, YYYY h:mm A")
                                        : "Unknown date"}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Table Data Dialog */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 break-all">
                            <TableIcon className="h-5 w-5 text-blue-500 flex-shrink-0" />
                            {selectedTable?.table_name}
                        </DialogTitle>
                        <DialogDescription className="break-all">
                            {selectedTable?.original_filename} • {selectedTable?.row_count.toLocaleString()} rows • {selectedTable?.column_count} columns
                        </DialogDescription>
                    </DialogHeader>

                    <div className="flex-1 overflow-auto">
                        {loadingData ? (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                            </div>
                        ) : tableData && tableData.rows.length > 0 ? (
                            <div className="border rounded-lg">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            {tableData.columns.map((col, index) => (
                                                <TableHead key={index} className="font-semibold whitespace-nowrap">
                                                    {col}
                                                </TableHead>
                                            ))}
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {tableData.rows.map((row, rowIndex) => (
                                            <TableRow key={rowIndex}>
                                                {tableData.columns.map((col, colIndex) => (
                                                    <TableCell key={colIndex} className="max-w-xs truncate">
                                                        {row[col] !== null && row[col] !== undefined
                                                            ? String(row[col])
                                                            : <span className="text-gray-400 italic">null</span>}
                                                    </TableCell>
                                                ))}
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        ) : (
                            <div className="text-center py-8 text-gray-500">
                                No data available
                            </div>
                        )}

                        {tableData && (
                            <p className="text-xs text-gray-500 mt-4 text-center">
                                Showing first {tableData.total_returned} rows
                            </p>
                        )}
                    </div>
                </DialogContent>
            </Dialog>
        </>
    );
};

export default TableListSection;
