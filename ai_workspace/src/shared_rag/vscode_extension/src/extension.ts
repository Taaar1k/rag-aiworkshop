/**
 * VS Code Extension for Shared RAG Integration
 * 
 * Provides inline RAG queries, document context, and source display
 * directly within the VS Code editor.
 */

import * as vscode from 'vscode';
import { SharedRAGJSClient, SharedRAGError, AuthenticationError, APIError, ConnectionError } from './client';

// Global state
let client: SharedRAGJSClient | null = null;
let outputChannel: vscode.OutputChannel;

/**
 * Initialize the Shared RAG client with VS Code configuration
 */
function initializeClient(): SharedRAGJSClient {
    const config = vscode.workspace.getConfiguration('sharedRAG');
    
    const apiUrl = config.get<string>('apiUrl', 'http://localhost:8000');
    const apiKey = config.get<string>('apiKey', '');
    const timeout = config.get<number>('timeout', 30000);
    const maxRetries = config.get<number>('maxRetries', 3);
    
    client = new SharedRAGJSClient({
        baseURL: apiUrl,
        apiKey: apiKey,
        timeout: timeout,
        maxRetries: maxRetries
    });
    
    return client;
}

/**
 * Get the current client, initializing if necessary
 */
function getClient(): SharedRAGJSClient {
    if (!client) {
        client = initializeClient();
    }
    return client;
}

/**
 * Query the RAG system and display results in VS Code
 */
async function queryRAG(query: string): Promise<void> {
    try {
        const client = getClient();
        const result = await client.query(query);
        
        // Display results in output channel
        outputChannel.appendLine(`\n=== RAG Query Results ===`);
        outputChannel.appendLine(`Query: ${query}`);
        outputChannel.appendLine(`Answer: ${result.answer}`);
        outputChannel.appendLine(`Query Time: ${result.query_time_ms.toFixed(2)}ms`);
        
        if (result.sources.length > 0) {
            outputChannel.appendLine(`\nSources (${result.sources.length}):`);
            result.sources.forEach((source: any, index: number) => {
                outputChannel.appendLine(`\n[${index + 1}] Score: ${source.score?.toFixed(4) || 'N/A'}`);
                outputChannel.appendLine(`Content: ${source.content?.substring(0, 200) || 'N/A'}...`);
            });
        }
        
        outputChannel.show();
        
    } catch (error: any) {
        handleRAGError(error);
    }
}

/**
 * Handle RAG errors and display in VS Code
 */
function handleRAGError(error: any): void {
    let message = 'Unknown error';
    let severity: vscode.LogLevel = 'Error';
    
    if (error instanceof AuthenticationError) {
        message = 'Authentication failed. Please check your API key.';
        severity = 'Error';
    } else if (error instanceof APIError) {
        message = `API Error ${error.statusCode}: ${error.message}`;
        severity = 'Error';
    } else if (error instanceof ConnectionError) {
        message = `Connection failed. Is the RAG server running?`;
        severity = 'Warning';
    } else if (error instanceof SharedRAGError) {
        message = error.message;
        severity = 'Error';
    }
    
    vscode.window.showErrorMessage(message);
    outputChannel.appendLine(`[ERROR] ${message}`);
}

/**
 * Configure the RAG connection
 */
async function configureRAG(): Promise<void> {
    const config = vscode.workspace.getConfiguration('sharedRAG');
    
    const apiUrl = await vscode.window.showInputBox({
        prompt: 'Enter RAG API URL',
        value: config.get<string>('apiUrl', 'http://localhost:8000'),
        placeHolder: 'http://localhost:8000'
    });
    
    if (apiUrl) {
        await config.update('apiUrl', apiUrl, vscode.ConfigurationTarget.Global);
        vscode.window.showInformationMessage(`RAG API URL updated to: ${apiUrl}`);
    }
    
    const apiKey = await vscode.window.showInputBox({
        prompt: 'Enter API Key (optional)',
        value: config.get<string>('apiKey', ''),
        placeHolder: 'Leave empty for no authentication'
    });
    
    if (apiKey !== undefined) {
        await config.update('apiKey', apiKey, vscode.ConfigurationTarget.Global);
        vscode.window.showInformationMessage('API Key updated');
    }
}

/**
 * Show sources for the current selection
 */
async function showSourcesForSelection(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    
    if (!editor) {
        vscode.window.showWarningMessage('No active editor found');
        return;
    }
    
    const selection = editor.selection;
    const text = editor.document.getText(selection);
    
    if (!text) {
        vscode.window.showWarningMessage('No text selected');
        return;
    }
    
    try {
        const client = getClient();
        const sources = await client.getSources(text);
        
        outputChannel.appendLine(`\n=== Sources for Selection ===`);
        outputChannel.appendLine(`Selected Text: ${text.substring(0, 100)}...`);
        
        if (sources.length > 0) {
            sources.forEach((source: any, index: number) => {
                outputChannel.appendLine(`\n[${index + 1}] Score: ${source.score?.toFixed(4) || 'N/A'}`);
                outputChannel.appendLine(`Content: ${source.content?.substring(0, 200) || 'N/A'}...`);
            });
        } else {
            outputChannel.appendLine('No sources found.');
        }
        
        outputChannel.show();
        
    } catch (error: any) {
        handleRAGError(error);
    }
}

/**
 * Upload current document to RAG
 */
async function uploadCurrentDocument(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    
    if (!editor) {
        vscode.window.showWarningMessage('No active editor found');
        return;
    }
    
    const document = editor.document;
    const text = document.getText();
    
    try {
        const client = getClient();
        const docInfo = await client.uploadDocument(text, {
            documentId: document.uri.fsPath,
            metadata: {
                language: document.languageId,
                fileName: document.fileName
            }
        });
        
        vscode.window.showInformationMessage(
            `Document uploaded successfully. ID: ${docInfo.id}`
        );
        
    } catch (error: any) {
        handleRAGError(error);
    }
}

/**
 * Check server health
 */
async function checkHealth(): Promise<void> {
    try {
        const client = getClient();
        const status = await client.getHealthStatus();
        
        outputChannel.appendLine(`\n=== Server Health ===`);
        outputChannel.appendLine(JSON.stringify(status, null, 2));
        outputChannel.show();
        
        vscode.window.showInformationMessage('Server is healthy');
        
    } catch (error: any) {
        handleRAGError(error);
    }
}

/**
 * Activate the extension
 */
export function activate(context: vscode.ExtensionContext) {
    outputChannel = vscode.window.createOutputChannel('Shared RAG');
    
    // Register commands
    const commands = [
        vscode.commands.registerCommand('sharedRAG.query', async () => {
            const query = await vscode.window.showInputBox({
                prompt: 'Enter your query',
                placeHolder: 'What would you like to know?'
            });
            
            if (query) {
                await queryRAG(query);
            }
        }),
        
        vscode.commands.registerCommand('sharedRAG.configure', configureRAG),
        
        vscode.commands.registerCommand('sharedRAG.showSources', showSourcesForSelection),
        
        vscode.commands.registerCommand('sharedRAG.uploadDocument', uploadCurrentDocument),
        
        vscode.commands.registerCommand('sharedRAG.checkHealth', checkHealth)
    ];
    
    // Add commands to subscriptions
    commands.forEach(command => {
        context.subscriptions.push(command);
    });
    
    // Initialize client
    try {
        initializeClient();
        outputChannel.appendLine('Shared RAG extension activated');
    } catch (error: any) {
        outputChannel.appendLine(`Failed to initialize client: ${error}`);
    }
}

/**
 * Deactivate the extension
 */
export function deactivate() {
    if (client) {
        client.close();
    }
}
