import { WebSocketServer, WebSocket } from 'ws';
import { elizaLogger } from '@elizaos/core';
import type { Character } from '@elizaos/core';
import type { DirectClient } from '@elizaos/client-direct';
import fetch from 'node-fetch';
import { settings } from '@elizaos/core';

interface WebSocketMessage {
  type: string;
  content: string;
}

// Extend WebSocket type to include isAlive property
interface ExtendedWebSocket extends WebSocket {
  isAlive: boolean;
}

export class WebSocketHandler {
  private wss: WebSocketServer;
  private clients: Set<ExtendedWebSocket>;
  private directClient: DirectClient;
  private characters: Character[];
  private serverPort: number;

  constructor(port: number, directClient: DirectClient, characters: Character[]) {
    this.wss = new WebSocketServer({ 
      port,
      host: '0.0.0.0', // Listen on all network interfaces
      clientTracking: true,
      // Add keep-alive settings
      perMessageDeflate: false,
      maxPayload: 1048576 // 1MB
    });
    this.clients = new Set();
    this.directClient = directClient;
    this.characters = characters;
    this.serverPort = parseInt(settings.SERVER_PORT || "3000");

    this.setupWebSocketServer();
  }

  private setupWebSocketServer() {
    this.wss.on('connection', (ws: ExtendedWebSocket) => {
      elizaLogger.success('New WebSocket client connected');
      this.clients.add(ws);

      // Set up heartbeat
      ws.isAlive = true;
      ws.on('pong', () => {
        ws.isAlive = true;
      });

      // Send initial connection message
      ws.send(JSON.stringify({
        type: 'connected',
        message: 'Connected to TrendPup Assistant'
      }));

      // Set up ping interval
      const interval = setInterval(() => {
        if (ws.isAlive === false) {
          elizaLogger.warn('Client connection dead, terminating');
          return ws.terminate();
        }
        ws.isAlive = false;
        ws.ping();
      }, 30000); // Send ping every 30 seconds

      ws.on('message', async (data) => {
        try {
          const message: WebSocketMessage = JSON.parse(data.toString());
          
          if (message.type === 'message') {
            // For now, we'll use the first character as the default agent
            const character = this.characters[0];
            const agentId = character.id || character.name;
            
            try {
              // Log that we received a message
              elizaLogger.info(`Received message for agent ${agentId}: ${message.content}`);
              
              // Forward the message to the agent using HTTP API
              const response = await fetch(
                `http://localhost:${this.serverPort}/${agentId}/message`,
                {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    text: message.content,
                    userId: "user",
                    userName: "User",
                  }),
                }
              );

              if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
              }

              const data = await response.json();
              elizaLogger.info(`Received response from agent: ${JSON.stringify(data)}`);
              
              if (Array.isArray(data)) {
                // Send each message in the response back to the client
                data.forEach(message => {
                  ws.send(JSON.stringify({
                    type: 'message',
                    text: message.text
                  }));
                });
              } else {
                // Handle non-array response
                ws.send(JSON.stringify({
                  type: 'message',
                  text: 'Agent response format was unexpected'
                }));
              }
              
            } catch (error) {
              elizaLogger.error('Error processing message:', error);
              ws.send(JSON.stringify({
                type: 'error',
                message: 'Error processing your message'
              }));
            }
          }
        } catch (error) {
          elizaLogger.error('Error parsing WebSocket message:', error);
          ws.send(JSON.stringify({
            type: 'error',
            message: 'Invalid message format'
          }));
        }
      });

      ws.on('close', () => {
        elizaLogger.warn('Client disconnected');
        clearInterval(interval); // Clear the ping interval
        this.clients.delete(ws);
      });

      ws.on('error', (error) => {
        elizaLogger.error('WebSocket error:', error);
        clearInterval(interval); // Clear the ping interval
        this.clients.delete(ws);
      });
    });

    this.wss.on('error', (error) => {
      elizaLogger.error('WebSocket server error:', error);
    });
  }

  public close() {
    this.wss.close();
  }
} 