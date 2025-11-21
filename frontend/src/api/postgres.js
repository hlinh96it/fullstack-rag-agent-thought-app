import { apiPostgres } from "@/lib/axios";

export const postgresApi = {
    /**
     * Upload a CSV file to create a PostgreSQL table
     * @param {string} userId - The user ID
     * @param {File} file - The CSV file to upload
     * @param {string} tableName - Optional custom table name
     * @param {function} onProgress - Callback for upload progress
     * @returns {Promise} Response with table creation details
     */
    uploadCsv: async (userId, file, tableName, onProgress) => {
        const formData = new FormData();
        formData.append("file", file);
        if (tableName) {
            formData.append("table_name", tableName);
        }

        return await apiPostgres.post(`/upload/${userId}`, formData, {
            headers: {
                "Content-Type": "multipart/form-data",
            },
            onUploadProgress: (progressEvent) => {
                if (onProgress) {
                    const percentCompleted = Math.round(
                        (progressEvent.loaded * 100) / progressEvent.total
                    );
                    onProgress(percentCompleted);
                }
            },
        });
    },

    /**
     * Get all PostgreSQL tables for a user
     * @param {string} userId - The user ID
     * @returns {Promise} List of tables with metadata
     */
    getUserTables: async (userId) => {
        return await apiPostgres.get(`/tables/${userId}`);
    },

    /**
     * Get data from a specific table
     * @param {string} tableName - The table name
     * @param {number} limit - Maximum number of rows to return
     * @returns {Promise} Table data with columns and rows
     */
    getTableData: async (tableName, limit = 100) => {
        return await apiPostgres.get(`/table/${tableName}/data`, {
            params: { limit },
        });
    },

    /**
     * Delete a table from PostgreSQL and MongoDB
     * @param {string} userId - The user ID
     * @param {string} tableName - The table name to delete
     * @returns {Promise} Success response
     */
    deleteTable: async (userId, tableName) => {
        return await apiPostgres.delete(`/table/${userId}/${tableName}`);
    },
};
