/**
 * JavaScript Client SDK for Shared RAG System.
 * 
 * Provides programmatic access to the shared RAG system via REST API.
 * Supports authentication, error handling, and works in both Node.js and browser environments.
 */

// Type definitions for TypeScript support
/**
 * @typedef {Object} QueryResult
 * @property {string} answer - The generated answer
 * @property {Array<Object>} sources - Source documents
 * @property {Object} metadata - Response metadata
 * @property {number} query_time_ms - Query execution time in milliseconds
 */

/**
 * @typedef {Object} DocumentInfo
 * @property {string} id - Document ID
 * @property {string} content - Document content
 * @property {Object} metadata - Document metadata
 * @property {number} embedding_size - Size of embedding vector
 */

/**
 * @typedef {Object} QueryOptions
 * @property {number} top_k - Number of documents to retrieve
 * @property {Object} filters - Optional filters
 * @property {number} temperature - LLM temperature (0.0-1.0)
 * @property {number} max_tokens - Maximum tokens in response
 */

/**
 * @typedef {Object} EmbeddingResponse
 * @property {Array<number>} embedding - The embedding vector
 * @property {number} model - Model identifier
 * @property {number} usage - Token usage
 */

// Custom Error Classes
class SharedRAGError extends Error {
    constructor(message) {
        super(message);
        this.name = 'SharedRAGError';
    }
}

class AuthenticationError extends SharedRAGError {
    constructor(message = 'Invalid or expired API key') {
        super(message);
        this.name = 'AuthenticationError';
    }
}

class APIError extends SharedRAGError {
    constructor(statusCode, message, details = {}) {
        super(`API Error ${statusCode}: ${message}`);
        this.statusCode = statusCode;
        this.message = message;
        this.details = details;
        this.name = 'APIError';
    }
}

class ConnectionError extends SharedRAGError {
    constructor(message = 'Connection failed') {
        super(message);
        this.name = 'ConnectionError';
    }
}

class SharedRAGJSClient {
    /**
     * Initialize the Shared RAG JavaScript client.
     * 
     * @param {Object} options - Configuration options
     * @param {string} options.baseURL - URL of the RAG server (default: 'http://localhost:8000')
     * @param {string} [options.apiKey] - API key for authentication
     * @param {number} [options.timeout=30000] - Request timeout in milliseconds
     * @param {number} [options.maxRetries=3] - Maximum retry attempts
     * @param {boolean} [options.verifySSL=true] - Whether to verify SSL certificates
     */
    constructor(options = {}) {
        const {
            baseURL = 'http://localhost:8000',
            apiKey = null,
            timeout = 30000,
            maxRetries = 3,
            verifySSL = true
        } = options;

        this.baseURL = baseURL.replace(/\/+$/, ''); // Remove trailing slashes
        this.apiKey = apiKey || process.env?.RAG_API_KEY || null;
        this.timeout = timeout;
        this.maxRetries = maxRetries;
        this.verifySSL = verifySSL;

        // Build headers
        this.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'SharedRAG-JS-Client/1.0'
        };

        if (this.apiKey) {
            this.headers['Authorization'] = `Bearer ${this.apiKey}`;
        }

        console.log(`SharedRAGJSClient initialized: ${this.baseURL}`);
    }

    /**
     * Make an HTTP request with retry logic and error handling.
     * 
     * @param {string} method - HTTP method
     * @param {string} endpoint - API endpoint
     * @param {Object} [data] - Request body for POST requests
     * @param {Object} [params] - Query parameters
     * @returns {Promise<Object>} - JSON response
     */
    async _makeRequest(method, endpoint, data = null, params = {}) {
        const url = new URL(`${this.baseURL}${endpoint}`);
        
        // Add query parameters
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url.searchParams.append(key, value);
            }
        });

        const options = {
            method,
            headers: this.headers,
            timeout: this.timeout
        };

        if (data !== null && data !== undefined) {
            options.body = JSON.stringify(data);
        }

        let lastError = null;

        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                // Use fetch API (available in browsers and Node.js 18+)
                // For older Node.js versions, you can use node-fetch
                let response;
                
                if (typeof fetch !== 'undefined') {
                    response = await fetch(url.toString(), options);
                } else {
                    // Fallback for Node.js without native fetch
                    const nodeFetch = require('node-fetch');
                    response = await nodeFetch(url.toString(), options);
                }

                // Handle authentication errors
                if (response.status === 401) {
                    throw new AuthenticationError();
                }

                // Handle other error responses
                if (!response.ok) {
                    let errorDetails = {};
                    try {
                        errorDetails = await response.json();
                    } catch (e) {
                        errorDetails = { raw: await response.text() };
                    }

                    throw new APIError(
                        response.status,
                        response.statusText,
                        errorDetails
                    );
                }

                // Parse response
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return await response.json();
                } else {
                    return await response.text();
                }

            } catch (error) {
                if (error instanceof (AuthenticationError || APIError)) {
                    // Don't retry authentication or API errors
                    throw error;
                }

                lastError = error;
                console.warn(`Request failed (attempt ${attempt}/${this.maxRetries}): ${error.message}`);
            }
        }

        // All retries failed
        throw new ConnectionError(
            lastError?.message || 'All retry attempts failed'
        );
    }

    /**
     * Query the shared RAG system.
     * 
     * @param {string} query - The search query
     * @param {QueryOptions} [options] - Query options
     * @returns {Promise<QueryResult>} - Query result with answer and sources
     */
    async query(query, options = {}) {
        const {
            top_k = 5,
            filters = {},
            temperature = 0.7,
            max_tokens = 512
        } = options;

        const startTime = Date.now();

        const requestData = {
            model: 'shared-rag-v1',
            messages: [
                { role: 'user', content: query }
            ],
            temperature,
            max_tokens,
            top_k,
            filters
        };

        const response = await this._makeRequest(
            'POST',
            '/v1/chat/completions',
            requestData
        );

        const queryTime = Date.now() - startTime;

        // Parse response
        const choices = response.choices || [];
        if (!choices.length) {
            throw new APIError(500, 'No choices in response');
        }

        const message = choices[0].message || {};
        const answer = message.content || '';

        // Extract sources from metadata
        const sources = response.metadata?.sources || [];

        return {
            answer,
            sources,
            metadata: response.metadata || {},
            query_time_ms: queryTime
        };
    }

    /**
     * Upload a document to the shared vector store.
     * 
     * @param {string} content - Document content
     * @param {Object} options - Upload options
     * @returns {Promise<DocumentInfo>} - Document information
     */
    async uploadDocument(content, options = {}) {
        const {
            documentId = null,
            metadata = {}
        } = options;

        const requestData = {
            content,
            metadata
        };

        if (documentId) {
            requestData.id = documentId;
        }

        const response = await this._makeRequest(
            'POST',
            '/v1/documents',
            requestData
        );

        return {
            id: response.id || '',
            content,
            metadata: response.metadata || {},
            embedding_size: response.embedding_size || 0
        };
    }

    /**
     * Delete a document from the vector store.
     * 
     * @param {string} documentId - ID of document to delete
     * @returns {Promise<boolean>} - True if deletion was successful
     */
    async deleteDocument(documentId) {
        await this._makeRequest(
            'DELETE',
            `/v1/documents/${encodeURIComponent(documentId)}`
        );
        return true;
    }

    /**
     * List documents in the vector store.
     * 
     * @param {Object} options - List options
     * @returns {Promise<Array<Object>>} - List of documents
     */
    async listDocuments(options = {}) {
        const {
            limit = 100,
            offset = 0
        } = options;

        const response = await this._makeRequest(
            'GET',
            '/v1/documents',
            null,
            { limit, offset }
        );

        return response.documents || [];
    }

    /**
     * Get server health status.
     * 
     * @returns {Promise<Object>} - Server health information
     */
    async getHealthStatus() {
        return await this._makeRequest('GET', '/health');
    }

    /**
     * Get server information.
     * 
     * @returns {Promise<Object>} - Server configuration
     */
    async getServerInfo() {
        return await this._makeRequest('GET', '/info');
    }

    /**
     * Generate embedding for text.
     * 
     * @param {string} text - Text to embed
     * @returns {Promise<Array<number>>} - Embedding vector
     */
    async generateEmbedding(text) {
        const response = await this._makeRequest(
            'POST',
            '/v1/embeddings',
            { input: text }
        );

        const data = response.data || [];
        if (!data.length) {
            throw new APIError(500, 'No embedding in response');
        }

        return data[0].embedding || [];
    }

    /**
     * Close the client and clean up resources.
     */
    close() {
        // No resources to clean up for fetch-based client
        console.log('SharedRAGJSClient closed');
    }
}

// Export for both ES modules and CommonJS
export default SharedRAGJSClient;
export {
    SharedRAGJSClient,
    SharedRAGError,
    AuthenticationError,
    APIError,
    ConnectionError,
    QueryResult,
    DocumentInfo,
    QueryOptions,
    EmbeddingResponse
};

// CommonJS export for Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SharedRAGJSClient;
    module.exports.SharedRAGJSClient = SharedRAGJSClient;
    module.exports.SharedRAGError = SharedRAGError;
    module.exports.AuthenticationError = AuthenticationError;
    module.exports.APIError = APIError;
    module.exports.ConnectionError = ConnectionError;
}
