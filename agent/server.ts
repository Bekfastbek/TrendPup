import { WebSocketServer } from "ws";
import { startAgent } from "./src/index";
import { DirectClient } from "@elizaos/client-direct";

const directClient = new DirectClient();
const wss = new WebSocketServer({ port: 8080 });

wss.on("connection", (ws) => {
  console.log("Client connected");

  ws.on("message", async (message) => {
    try {
      const data = JSON.parse(message);

      if (data.type === "startAgent" && data.character) {
        const agent = await startAgent(data.character, directClient);
        ws.send(JSON.stringify({ status: "success", agentId: agent.agentId }));
      } else {
        ws.send(JSON.stringify({ status: "error", message: "Invalid request" }));
      }
    } catch (error) {
      console.error("Error processing message:", error);
      ws.send(JSON.stringify({ status: "error", message: error.message }));
    }
  });

  ws.on("close", () => {
    console.log("Client disconnected");
  });
});

console.log("WebSocket server running on ws://localhost:8080");
