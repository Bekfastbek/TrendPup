'use client';

import { useState, useEffect, useRef } from 'react';
import { IoSendSharp } from 'react-icons/io5';
import { FaDog, FaUser } from 'react-icons/fa';
import Image from 'next/image';

interface Message {
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatInterfaceProps {
  fullPage?: boolean;
}

export default function ChatInterface({ fullPage = false }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const socket = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);

      socket.onopen = () => {
        setIsConnected(true);
      };

      socket.onclose = () => {
        setIsConnected(false);
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: 'Connection lost. Please refresh the page to reconnect.',
          timestamp: new Date()
        }]);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'connected') {
            setMessages(prev => [...prev, {
              type: 'assistant',
              content: 'Hello! I\'m TrendPup, your AI assistant for memecoin intelligence. How can I help you discover the next big opportunity?',
              timestamp: new Date()
            }]);
          } else if (data.type === 'message' && data.text) {
            setIsTyping(false);
            setMessages(prev => [...prev, {
              type: 'assistant',
              content: data.text,
              timestamp: new Date()
            }]);
          } else if (data.type === 'error') {
            setIsTyping(false);
            setMessages(prev => [...prev, {
              type: 'assistant',
              content: `Error: ${data.message}`,
              timestamp: new Date()
            }]);
          }
        } catch (err) {
          console.error('Error parsing message:', err);
        }
      };

      setWs(socket);

      return () => {
        socket.close();
      };
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = () => {
    if (!ws || !input.trim() || !isConnected) return;

    // Add user message to chat
    setMessages(prev => [...prev, {
      type: 'user',
      content: input,
      timestamp: new Date()
    }]);

    // Show typing indicator
    setIsTyping(true);

    // Send message to server
    ws.send(JSON.stringify({
      type: 'message',
      content: input
    }));

    setInput('');
    inputRef.current?.focus();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const containerHeight = fullPage ? 'h-[calc(100vh-8rem)]' : 'h-[calc(100vh-12rem)]';

  return (
    <div className={`flex flex-col ${containerHeight} max-w-4xl mx-auto rounded-xl shadow-xl overflow-hidden border border-trendpup-brown/20 bg-white`}>
      {!fullPage && (
        <div className="bg-trendpup-dark text-white p-4 flex items-center">
          <div className="flex-shrink-0 mr-3">
            <Image 
              src="/trendpup-logo.png" 
              alt="TrendPup Logo" 
              width={32} 
              height={32}
            />
          </div>
          <div>
            <h1 className="text-xl font-semibold">TrendPup Assistant</h1>
            <p className="text-sm opacity-75">
              {isConnected ? 'Online - Ready to spot trends' : 'Connecting...'}
            </p>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 bg-trendpup-light">
        <div className="space-y-4">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex items-start max-w-[80%] ${msg.type === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${
                  msg.type === 'user' ? 'bg-trendpup-orange ml-2' : 'bg-trendpup-brown mr-2'
                }`}>
                  {msg.type === 'user' ? (
                    <FaUser className="text-white text-sm" />
                  ) : (
                    <FaDog className="text-white text-sm" />
                  )}
                </div>
                <div
                  className={`rounded-lg p-3 ${
                    msg.type === 'user'
                      ? 'bg-trendpup-orange text-white'
                      : 'bg-white text-trendpup-dark border border-trendpup-brown/20'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  <span className="text-xs opacity-75 mt-1 block">
                    {formatTimestamp(msg.timestamp)}
                  </span>
                </div>
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex justify-start">
              <div className="flex items-start">
                <div className="flex-shrink-0 h-8 w-8 rounded-full bg-trendpup-brown mr-2 flex items-center justify-center">
                  <FaDog className="text-white text-sm" />
                </div>
                <div className="bg-white text-gray-800 rounded-lg p-3 border border-trendpup-brown/20">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-trendpup-brown rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-trendpup-brown rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-trendpup-brown rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="p-4 bg-white border-t border-trendpup-brown/10">
        <div className="flex items-end space-x-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={isConnected ? "Ask about memecoins, trends, or market insights..." : "Connecting..."}
            disabled={!isConnected}
            className="flex-1 p-3 border border-trendpup-brown/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-trendpup-orange resize-none h-12 max-h-32 min-h-[3rem]"
            rows={1}
          />
          <button
            onClick={sendMessage}
            disabled={!isConnected || !input.trim()}
            className="p-3 bg-trendpup-orange text-white rounded-lg hover:bg-orange-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            <IoSendSharp className="text-xl" />
          </button>
        </div>
      </div>
    </div>
  );
} 