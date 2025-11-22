import { apiPostgres } from "@/lib/axios";

export const postgresApi = {
    /**
     * Upload a CSV file to create a PostgreSQL table
     * @param {string} userId - The user ID
     * @param {File} file - The CSV file to upload
     * @param {string} tableName - Optional custom table name
     * @param {string} databaseName - Optional database name
     * @param {function} onProgress - Callback for upload progress
     * @returns {Promise} Response with table creation details
     */
    uploadCsv: async (userId, file, tableName, databaseName, onProgress) => {
        const formData = new FormData();
        formData.append("file", file);
        if (tableName) {
            formData.append("table_name", tableName);
        }
        if (databaseName) {
            formData.append("database_name", databaseName);
        }

        return await apiPostgres.post(`/upload/${userId}/${databaseName}`, formData, {
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
     * Get all PostgreSQL tables for a user in a specific database
     * @param {string} userId - The user ID
     * @param {string} databaseName - The database name
     * @returns {Promise} List of tables with metadata
     */
    getUserTables: async (userId, databaseName) => {
        return await apiPostgres.get(`/tables/${userId}/${databaseName}`);
    },

    /**
     * Get data from a specific table
     * @param {string} tableName - The table name
     * @param {string} databaseName - The database name
     * @param {number} limit - Maximum number of rows to return
     * @returns {Promise} Table data with columns and rows
     */
    getTableData: async (tableName, databaseName, limit = 100) => {
        const params = { limit };
        if (databaseName) {
            params.database_name = databaseName;
        }
        return await apiPostgres.get(`/table/${tableName}/data`, {
            params,
        });
    },

    /**
     * Delete a table from PostgreSQL and MongoDB
     * @param {string} userId - The user ID
     * @param {string} databaseName - The database name
     * @param {string} tableName - The table name to delete
     * @returns {Promise} Success response
     */
    deleteTable: async (userId, databaseName, tableName) => {
        return await apiPostgres.delete(`/table/${userId}/${databaseName}/${tableName}`);
    },

    /**
     * Get all available databases for a user
     * @param {string} userId - The user ID
     * @returns {Promise} List of databases
     */
    listDatabases: async (userId) => {
        return await apiPostgres.get(`/databases/${userId}`);
    },

    /**
     * Create a new database
     * @param {string} userId - The user ID
     * @param {string} databaseName - The name of the database to create
     * @returns {Promise} Success response
     */
    createDatabase: async (userId, databaseName) => {
        const formData = new FormData();
        formData.append("database_name", databaseName);
        return await apiPostgres.post(`/database/create/${userId}`, formData, {
            headers: {
                "Content-Type": "multipart/form-data",
            },
        });
    },

    /**
     * Delete a database
     * @param {string} userId - The user ID
     * @param {string} databaseName - The name of the database to delete
     * @returns {Promise} Success response
     */
    deleteDatabase: async (userId, databaseName) => {
        return await apiPostgres.delete(`/database/${userId}/${databaseName}`);
    },

    /**
     * Sync databases and tables between PostgreSQL and MongoDB
     * @param {string} userId - The user ID
     * @returns {Promise} Sync summary with changes
     */
    syncDatabases: async (userId) => {
        return await apiPostgres.post(`/sync/${userId}`);
    },
};
