'use client';

import { useState } from 'react';
import { FaSearch, FaChartLine, FaRegStar, FaStar, FaInfoCircle } from 'react-icons/fa';
import Image from 'next/image';

interface Memecoin {
  id: number;
  name: string;
  symbol: string;
  logo: string;
  price: number;
  change24h: number;
  marketCap: number;
  risk: number;
  potential: number;
  favorite: boolean;
}

export default function MemecoinsExplorer() {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('trending');
  
  // Sample data for demonstration
  const [memecoins, setMemecoins] = useState<Memecoin[]>([
    {
      id: 1,
      name: 'Doge Coin',
      symbol: 'DOGE',
      logo: '/trendpup-logo.png',
      price: 0.12,
      change24h: 5.2,
      marketCap: 18000000,
      risk: 3,
      potential: 7,
      favorite: true
    },
    {
      id: 2,
      name: 'Shiba Inu',
      symbol: 'SHIB',
      logo: '/trendpup-logo.png',
      price: 0.000028,
      change24h: -2.1,
      marketCap: 14000000,
      risk: 5,
      potential: 6,
      favorite: false
    },
    {
      id: 3,
      name: 'PepeCoin',
      symbol: 'PEPE',
      logo: '/trendpup-logo.png',
      price: 0.000008,
      change24h: 12.4,
      marketCap: 9800000,
      risk: 8,
      potential: 9,
      favorite: false
    },
    {
      id: 4,
      name: 'Bonk',
      symbol: 'BONK',
      logo: '/trendpup-logo.png',
      price: 0.00002,
      change24h: 3.5,
      marketCap: 7500000,
      risk: 7,
      potential: 8,
      favorite: true
    },
    {
      id: 5,
      name: 'Floki Inu',
      symbol: 'FLOKI',
      logo: '/trendpup-logo.png',
      price: 0.0002,
      change24h: -1.3,
      marketCap: 8700000,
      risk: 6,
      potential: 7,
      favorite: false
    }
  ]);

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
              {displayedCoins.map((coin) => (
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
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
} 