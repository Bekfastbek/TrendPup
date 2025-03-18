'use client';

import { useState, useEffect } from 'react';
import { FaSearch, FaChartLine, FaRegStar, FaStar, FaInfoCircle, FaSpinner } from 'react-icons/fa';
import Image from 'next/image';
import { fetchHelixData, FormattedMemecoin } from '../services/helixData';

export default function MemecoinsExplorer() {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('trending');
  const [memecoins, setMemecoins] = useState<FormattedMemecoin[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadHelixData() {
      try {
        setIsLoading(true);
        const data = await fetchHelixData();
        setMemecoins(data);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch helix data:', err);
        setError('Failed to load memecoin data. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    }

    loadHelixData();
  }, []);

  const toggleFavorite = (id: number) => {
    setMemecoins(prevCoins => 
      prevCoins.map(coin => 
        coin.id === id ? { ...coin, favorite: !coin.favorite } : coin
      )
    );
  };

  const filteredCoins = memecoins.filter(coin => 
    coin.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    coin.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const displayedCoins = activeTab === 'trending' 
    ? filteredCoins.sort((a, b) => b.potential - a.potential)
    : activeTab === 'favorites' 
    ? filteredCoins.filter(coin => coin.favorite)
    : filteredCoins.sort((a, b) => a.risk - b.risk);

  return (
    <div className="bg-white rounded-xl shadow-lg border border-trendpup-brown/20 overflow-hidden">
      <div className="p-4 bg-trendpup-dark text-white">
        <h2 className="text-xl font-bold">Memecoin Explorer</h2>
        <p className="text-sm opacity-75">Discover trending memecoins with TrendPup intelligence</p>
      </div>
      
      <div className="p-4">
        <div className="relative mb-4">
          <input
            type="text"
            placeholder="Search coins..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full p-3 pl-10 border border-trendpup-brown/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-trendpup-orange"
          />
          <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        </div>
        
        <div className="flex mb-4 border-b border-trendpup-brown/10">
          <button
            onClick={() => setActiveTab('trending')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'trending' 
                ? 'text-trendpup-orange border-b-2 border-trendpup-orange' 
                : 'text-gray-500 hover:text-trendpup-orange'
            }`}
          >
            Trending
          </button>
          <button
            onClick={() => setActiveTab('favorites')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'favorites' 
                ? 'text-trendpup-orange border-b-2 border-trendpup-orange' 
                : 'text-gray-500 hover:text-trendpup-orange'
            }`}
          >
            Favorites
          </button>
          <button
            onClick={() => setActiveTab('safe')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'safe' 
                ? 'text-trendpup-orange border-b-2 border-trendpup-orange' 
                : 'text-gray-500 hover:text-trendpup-orange'
            }`}
          >
            Safest
          </button>
        </div>
        
        {isLoading ? (
          <div className="flex justify-center items-center py-10">
            <FaSpinner className="animate-spin text-trendpup-orange text-3xl" />
            <span className="ml-2 text-gray-600">Loading memecoin data...</span>
          </div>
        ) : error ? (
          <div className="text-center py-10 text-red-500">
            <FaInfoCircle className="text-3xl mb-2 inline-block" />
            <p>{error}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-trendpup-beige">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-trendpup-dark uppercase tracking-wider">Coin</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-trendpup-dark uppercase tracking-wider">Price</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-trendpup-dark uppercase tracking-wider">24h</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-trendpup-dark uppercase tracking-wider">Market Cap</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-trendpup-dark uppercase tracking-wider">Risk</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-trendpup-dark uppercase tracking-wider">Potential</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-trendpup-dark uppercase tracking-wider">Favorite</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-trendpup-beige/50">
                {displayedCoins.length > 0 ? (
                  displayedCoins.map((coin) => (
                    <tr key={coin.id} className="hover:bg-trendpup-beige/20">
                      <td className="px-4 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-8 w-8 rounded-full overflow-hidden">
                            <Image src={coin.logo} alt={coin.name} width={32} height={32} />
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-trendpup-dark">{coin.name}</div>
                            <div className="text-xs text-gray-500">{coin.symbol}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium">
                        ${coin.price.toFixed(coin.price < 0.001 ? 8 : 6)}
                      </td>
                      <td className={`px-4 py-4 whitespace-nowrap text-right text-sm font-medium ${
                        coin.change24h >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {coin.change24h >= 0 ? '+' : ''}{coin.change24h}%
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-right text-sm text-gray-500">
                        ${(coin.marketCap / 1000000).toFixed(2)}M
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-center">
                        <div className="flex items-center justify-center">
                          <div className="w-24 bg-gray-200 rounded-full h-2.5">
                            <div 
                              className={`h-2.5 rounded-full ${
                                coin.risk <= 3 ? 'bg-green-500' : 
                                coin.risk <= 6 ? 'bg-yellow-500' : 'bg-red-500'
                              }`} 
                              style={{ width: `${coin.risk * 10}%` }}
                            ></div>
                          </div>
                          <span className="ml-2 text-xs text-gray-500">{coin.risk}/10</span>
                        </div>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-center">
                        <div className="flex items-center justify-center">
                          <div className="w-24 bg-gray-200 rounded-full h-2.5">
                            <div 
                              className="h-2.5 bg-trendpup-orange rounded-full" 
                              style={{ width: `${coin.potential * 10}%` }}
                            ></div>
                          </div>
                          <span className="ml-2 text-xs text-gray-500">{coin.potential}/10</span>
                        </div>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-center">
                        <button 
                          onClick={() => toggleFavorite(coin.id)}
                          className="text-lg"
                        >
                          {coin.favorite ? 
                            <FaStar className="text-trendpup-orange" /> : 
                            <FaRegStar className="text-gray-400 hover:text-trendpup-orange" />
                          }
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-gray-500">
                      No memecoins found matching your search criteria
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
} 