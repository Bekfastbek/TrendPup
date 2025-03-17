'use client';

import { useState, useEffect, useCallback } from 'react';

interface BalanceResponse {
  text: string;
  content: {
    accountAddress: string;
    denom: string;
    amount: string;
    formattedAmount: string;
  };
}

export default function BalanceChecker() {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [address, setAddress] = useState('');
  const [balance, setBalance] = useState<BalanceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const socket = new WebSocket(`${wsProtocol}//${window.location.hostname}:8080`);
      
      socket.onopen = () => {
        setIsConnected(true);
        console.log('Connected to balance checker');
      };
      
      socket.onclose = () => {
        setIsConnected(false);
        setError('Connection to server lost');
      };

      socket.onerror = (error) => {
        setError('WebSocket error occurred');
        console.error('WebSocket error:', error);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          switch (data.type) {
            case 'connected':
              setError(null);
              break;
            
            case 'balanceResponse':
              setBalance(data);
              setIsLoading(false);
              break;
            
            case 'error':
              setError(data.message);
              setIsLoading(false);
              break;
            
            default:
              console.log('Received message:', data);
          }
        } catch (err) {
          console.error('Error parsing message:', err);
          setError('Error processing server response');
          setIsLoading(false);
        }
      };

      setWs(socket);

      return () => {
        socket.close();
      };
    }
  }, []);

  const checkBalance = useCallback(() => {
    if (!ws || !address) return;

    setIsLoading(true);
    setError(null);
    setBalance(null);

    ws.send(JSON.stringify({
      type: 'checkBalance',
      address: address
    }));
  }, [ws, address]);

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Injective Balance Checker</h1>
      
      <div className="mb-6">
        <div className="flex gap-4">
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Enter Injective address (inj1...)"
            className="flex-1 p-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={checkBalance}
            disabled={!isConnected || !address || isLoading}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Checking...' : 'Check Balance'}
          </button>
        </div>
        
        {!isConnected && (
          <p className="text-yellow-600 mt-2">
            Connecting to server...
          </p>
        )}
      </div>

      {error && (
        <div className="p-4 bg-red-100 border border-red-400 rounded mb-4">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {balance && (
        <div className="p-4 bg-green-100 border border-green-400 rounded">
          <h2 className="font-semibold mb-2">Balance Information</h2>
          <p className="text-lg">{balance.text}</p>
          <div className="mt-2 text-sm text-gray-600">
            <p>Address: {balance.content.accountAddress}</p>
            <p>Amount: {balance.content.formattedAmount} {balance.content.denom.toUpperCase()}</p>
          </div>
        </div>
      )}
    </div>
  );
} 