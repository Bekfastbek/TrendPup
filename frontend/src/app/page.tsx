"use client"; // Needed for client-side hooks

import ChatInterface from './components/ChatInterface';

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-100">
      <ChatInterface />
    </main>
  );
}
