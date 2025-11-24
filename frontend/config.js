// This file will be overridden by the backend endpoint /config.js
// But included as fallback for static serving

// Default configuration
window.WEBSOCKET_URL = window.WEBSOCKET_URL || 
  (window.location.hostname.includes('railway.app') 
    ? `wss://${window.location.host}/ws/ai` 
    : 'ws://localhost:8000/ws/ai');

console.log('Static WebSocket URL configured:', window.WEBSOCKET_URL);