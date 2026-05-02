/**
 * JavaScript Client SDK for Shared RAG System.
 * 
 * Provides programmatic access to the shared RAG system via REST API.
 * Supports authentication, error handling, and works in both Node.js and browser environments.
 */

// Type definitions for TypeScript support
export interface QueryResult {
    answer: string;
    sources: Array<{content: string, score?: number}>;
    metadata: Record<string, any>;
    query_time_ms: number;
}

export interface DocumentInfo {
    id: string;
    content: string;
    metadata: Record<string, any>;
    embedding_size: number;
}

export interface QueryOptions {
    top_k?: number;
    filters?: Record<string, any>;
    temperature?: number;
    max_tokens?: number;
}

// Custom Error Classes
export class SharedRAGError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'SharedRAGError';
    }
}

export class AuthenticationError extends SharedRAGError {
    constructor(message: string = 'Invalid or expired API key') {
        super(message);
        this.name = 'AuthenticationError';
    }
}

export class APIError extends SharedRAGError {
    constructor(public statusCode: number, message: string, public details: Record<string, any> = {}) {
        super(`API Error ${statusCode}: ${message}`);
        this.name = 'APIError';
    }
}

export class ConnectionError extends SharedRAGError {
    constructor(message: string = 'Connection failed') {
        super(message);
        this.name = 'ConnectionError';
    }
}

export class SharedRAGJSClient {
    private baseURL: string;
    private apiKey: string | null;
    private timeout: number;
    private maxRetries: number;
    private headers: Record<string, string>;

    /**
     * Initialize the Shared RAG JavaScript client.
     */
    constructor(options: {
        baseURL?: string;
        apiKey?: string;
        timeout?: number;
        maxRetries?: number;
    } = {}) {
        const {
            baseURL = 'http://localhost:8000',
            apiKey = null,
            timeout = 30000,
            maxRetries = 3
        } = options;

        this.baseURL = baseURL.replace(/\/+$/, '');
        this.apiKey = apiKey;
        this.timeout = timeout;
        this.maxRetries = maxRetries;

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
     */
    private async _makeRequest(
        method: string,
        endpoint: string,
        data: any = null,
        params: Record<string, any> = {}
    ): Promise<any> {
        const url = new URL(`${this.baseURL}${endpoint}`);
        
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url.searchParams.append(key, value);
            }
        });

        const options: RequestInit = {
            method,
            headers: this.headers,
            timeout: this.timeout
        };

        if (data !== null && data !== undefined) {
            options.body = JSON.stringify(data);
        }

        let lastError: Error | null = null;

        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                const response = await fetch(url.toString(), options);

                if (response.status === 401) {
                    throw new AuthenticationError();
                }

                if (!response.ok) {
                    let errorDetails: Record<string, any> = {};
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

                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return await response.json();
                } else {
                    return await response.text();
                }

            } catch (error: any) {
                if (error instanceof (AuthenticationError || APIError)) {
                    throw error;
                }

                lastError = error;
                console.warn(`Request failed (attempt ${attempt}/${this.maxRetries}): ${error.message}`);
            }
        }

        throw new ConnectionError(
            lastError?.message || 'All retry attempts failed'
        );
    }

    /**
     * Query the shared RAG system.
     */
    async query(query: string, options: QueryOptions = {}): Promise<QueryResult> {
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

        const choices = response.choices || [];
        if (!choices.length) {
            throw new APIError(500, 'No choices in response');
        }

        const message = choices[0].message || {};
        const answer = message.content || '';

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
     */
    async uploadDocument(content: string, options: {
        documentId?: string;
        metadata?: Record<string, any>;
    } = {}): Promise<DocumentInfo> {
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
     */
    async deleteDocument(documentId: string): Promise<boolean> {
        await this._makeRequest(
            'DELETE',
            `/v1/documents/${encodeURIComponent(documentId)}`
        );
        return true;
    }

    /**
     * List documents in the vector store.
     */
    async listDocuments(options: {
        limit?: number;
        offset?: number;
    } = {}): Promise<Array<Record<string, any>>> {
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
     */
    async getHealthStatus(): Promise<Record<string, any>> {
        return await this._makeRequest('GET', '/health');
    }

    /**
     * Get server information.
     */
    async getServerInfo(): Promise<Record<string, any>> {
        return await this._makeRequest('GET', '/info');
    }

    /**
     * Generate embedding for text.
     */
    async generateEmbedding(text: string): Promise<Array<number>> {
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
    close(): void {
        console.log('SharedRAGJSClient closed');
    }
}

export default SharedRAGJSClient;
