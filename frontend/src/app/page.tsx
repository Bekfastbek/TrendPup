"use client"; // Needed for client-side hooks

import { useEffect, useState } from "react";

export default function Home() {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [messages, setMessages] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const socket = new WebSocket("ws://localhost:8080"); // Change URL if needed

    socket.onopen = () => {
      console.log("Connected to WebSocket");
      setConnected(true);
    };

    socket.onmessage = (event) => {
      setMessages((prev) => [...prev, event.data]);
    };

    socket.onclose = () => {
      console.log("Disconnected from WebSocket");
      setConnected(false);
    };

    setWs(socket);

    return () => {
      socket.close();
    };
  }, []);

  const startAgent = () => {
    if (ws) {
      ws.send(JSON.stringify({ type: "startAgent", name: "InjectiveAssistant" }));
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <h1 className="text-3xl font-bold mb-4">WebSocket Test</h1>
      <button
        onClick={startAgent}
        disabled={!connected}
        className="px-4 py-2 bg-blue-500 text-white rounded disabled:bg-gray-400"
      >
        Start Agent
      </button>
      <div className="mt-4 p-4 bg-white shadow-md rounded w-1/2">
        <h2 className="text-xl font-semibold">Messages</h2>
        <div className="h-40 overflow-y-auto">
          {messages.map((msg, index) => (
            <p key={index} className="text-sm">
              {msg}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}
