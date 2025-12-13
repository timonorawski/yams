/**
 * IDE Bridge - JavaScript side
 *
 * Receives project files from the Monaco IDE via postMessage and queues
 * them for Python to process. Also handles responses back to the IDE.
 *
 * Message protocol:
 *
 * IDE → Engine:
 *   {type: 'project_files', files: {'game.json': {...}, 'lua/foo.lua': '...'}}
 *   {type: 'reload'}
 *   {type: 'ping'}  // Health check
 *
 * Engine → IDE:
 *   {type: 'ready'}
 *   {type: 'files_received', filesWritten: 5}
 *   {type: 'reloaded'}
 *   {type: 'error', message: '...', file: '...', line: 42}
 *   {type: 'log', level: 'info', message: '...'}
 *   {type: 'pong'}
 */

(function() {
    'use strict';

    // Message queue for Python to poll
    window.ideMessages = window.ideMessages || [];

    // Flag to indicate IDE mode is active
    window.ideMode = false;

    // Project path (set by Python after init)
    window.ideProjectPath = '';

    /**
     * Send message back to IDE (parent window)
     */
    function sendToIDE(type, data = {}) {
        const message = {
            source: 'ams_engine',
            type: type,
            ...data,
            timestamp: Date.now()
        };
        try {
            window.parent.postMessage(message, '*');
        } catch (e) {
            console.error('[IDE Bridge] Failed to send to IDE:', e);
        }
    }

    /**
     * Handle incoming message from IDE
     */
    function handleIDEMessage(event) {
        // Ignore messages from same window or without proper structure
        if (event.source === window) return;
        if (!event.data || typeof event.data !== 'object') return;

        const msg = event.data;

        // Check for IDE message marker
        if (msg.source !== 'ams_ide') return;

        console.log('[IDE Bridge] Received:', msg.type);

        switch (msg.type) {
            case 'project_files':
                // Queue files for Python to process
                window.ideMessages.push({
                    type: 'files',
                    files: msg.files,
                    timestamp: Date.now()
                });
                window.ideMode = true;
                console.log('[IDE Bridge] Queued', Object.keys(msg.files || {}).length, 'files for Python');
                break;

            case 'reload':
                // Queue reload request
                window.ideMessages.push({
                    type: 'reload',
                    timestamp: Date.now()
                });
                console.log('[IDE Bridge] Queued reload request');
                break;

            case 'ping':
                // Immediate response - no Python needed
                sendToIDE('pong', {ideMode: window.ideMode});
                break;

            default:
                console.log('[IDE Bridge] Unknown message type:', msg.type);
        }
    }

    /**
     * Initialize the bridge
     * Called automatically when script loads
     */
    function init() {
        // Listen for messages from parent window (IDE)
        window.addEventListener('message', handleIDEMessage);

        // Expose functions for Python to call
        window.ideBridge = {
            sendToIDE: sendToIDE,

            // Python-safe version that accepts JSON string
            sendToIDEFromPython: function(type, dataJson) {
                const data = dataJson ? JSON.parse(dataJson) : {};
                sendToIDE(type, data);
            },

            // Called by Python after processing files
            notifyFilesReceived: function(filesWritten) {
                sendToIDE('files_received', {filesWritten: filesWritten});
            },

            // Called by Python after reload
            notifyReloaded: function() {
                sendToIDE('reloaded');
            },

            // Called by Python on error
            notifyError: function(message, file, line) {
                sendToIDE('error', {message: message, file: file || null, line: line || null});
            },

            // Called by Python to send log
            notifyLog: function(level, message, module) {
                sendToIDE('log', {
                    level: level || 'INFO',
                    message: message,
                    module: module || 'Engine'
                });
            },

            // Check if there are pending messages
            hasPendingMessages: function() {
                return window.ideMessages.length > 0;
            },

            // Get next message (returns null if empty)
            getNextMessage: function() {
                return window.ideMessages.shift() || null;
            },

            // Get all pending messages and clear queue
            getAllMessages: function() {
                const msgs = window.ideMessages;
                window.ideMessages = [];
                return msgs;
            }
        };

        // Note: We do NOT send 'ready' here - Python will send it after initialization
        // This prevents PreviewFrame from sending files before Python is ready to receive them
        console.log('[IDE Bridge] Initialized (waiting for Python to signal ready)');
    }

    // Initialize on load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
