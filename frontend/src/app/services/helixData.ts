interface HelixCoin {
  symbol: string;
  price: string;
  volume: string;
  change_24h: string;
  timestamp: string;
  market_id?: string;
  market_name?: string;
  tick_size?: string;
  min_limit_order_size?: string;
  volume_24h?: string;
  high_24h?: string;
  low_24h?: string;
  helix_link?: string;
}

interface HelixDataResponse {
  data: HelixCoin[];
}

export interface FormattedMemecoin {
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
  marketId?: string;
  helixLink?: string;
  tickSize?: string;
  minOrderSize?: string;
  high24h?: number;
  low24h?: number;
}

// Function to parse price strings, handling various formats
const parsePrice = (priceStr: string): number => {
  // Remove commas and any non-numeric characters except dots
  const cleaned = priceStr.replace(/,/g, '').replace(/[^\d.-]/g, '');
  
  // Parse the cleaned string
  const price = parseFloat(cleaned);
  
  // If parsing fails or results in NaN, return 0
  return isNaN(price) ? 0 : price;
};

// Function to parse percentage change
const parseChange = (changeStr: string): number => {
  if (changeStr === 'N/A') return 0;
  
  // Extract the number and remove the % sign
  const cleaned = changeStr.replace(/[^\d.-]/g, '');
  
  // Parse the cleaned string
  const change = parseFloat(cleaned);
  
  // If parsing fails or results in NaN, return 0
  return isNaN(change) ? 0 : change;
};

// Function to determine risk score based on price volatility and other factors
const calculateRisk = (price: number, changeStr: string): number => {
  const change = parseChange(changeStr);
  
  // Higher volatility means higher risk
  const volatilityRisk = Math.min(Math.abs(change), 10);
  
  // Very low-priced coins are generally riskier
  const priceRisk = price < 0.001 ? 8 : price < 0.01 ? 6 : price < 0.1 ? 5 : 3;
  
  // Return weighted average
  return Math.min(Math.round((volatilityRisk * 0.6 + priceRisk * 0.4)), 10);
};

// Function to determine potential score
const calculatePotential = (price: number, changeStr: string): number => {
  const change = parseChange(changeStr);
  
  // Coins with positive recent changes have higher potential
  const changePotential = change > 5 ? 8 : change > 0 ? 6 : 4;
  
  // Low-priced coins have higher potential for big percentage moves
  const pricePotential = price < 0.001 ? 9 : price < 0.01 ? 7 : price < 0.1 ? 6 : 5;
  
  // Return weighted average
  return Math.min(Math.round((changePotential * 0.5 + pricePotential * 0.5)), 10);
};

// Helper function to parse price strings to numbers
const parseNumericValue = (valueStr: string | undefined): number => {
  if (!valueStr || valueStr === 'N/A') return 0;
  
  // Remove commas, currency symbols, and any non-numeric characters except dots
  const cleaned = valueStr.replace(/,/g, '').replace(/[^\d.-]/g, '');
  
  // Parse the cleaned string
  const value = parseFloat(cleaned);
  
  // If parsing fails or results in NaN, return 0
  return isNaN(value) ? 0 : value;
};

// Fallback data - sample of helix_detailed_data.json content
const fallbackData: HelixDataResponse = {
  data: [
    {
      "symbol": "HINJ/INJ",
      "price": "1",
      "volume": "N/A",
      "change_24h": "+0.09%",
      "timestamp": "2025-03-18T17:54:51.946Z",
      "market_id": "0x1b1e062b3306f26ae3af3c354a10c1cf38b00dcb42917f038ba3fc14978b1dd8",
      "market_name": "hINJ/INJ",
      "tick_size": "0.0001",
      "min_limit_order_size": "0.001",
      "volume_24h": "16,183.328 INJ",
      "high_24h": "0.9941",
      "low_24h": "0.9901",
      "helix_link": "https://helixapp.com/spot/hinj-inj"
    },
    {
      "symbol": "STINJ/INJ",
      "price": "1.3816",
      "volume": "N/A",
      "change_24h": "+0.03%",
      "timestamp": "2025-03-18T17:54:51.947Z",
      "market_id": "0x2a3e06be3b6c13730f801c66010b355c3d28d5bd4ee736eeabbfa56e0a735b58"
    },
    {
      "symbol": "HDRO/INJ",
      "price": "0.001931",
      "volume": "N/A",
      "change_24h": "+6.51%",
      "timestamp": "2025-03-18T17:54:51.947Z"
    },
    {
      "symbol": "NEPT/INJ",
      "price": "0.03867",
      "volume": "N/A",
      "change_24h": "+6.18%",
      "timestamp": "2025-03-18T17:54:51.948Z"
    },
    {
      "symbol": "AGENT/INJ",
      "price": "0.03247",
      "volume": "N/A",
      "change_24h": "-1.00%",
      "timestamp": "2025-03-18T17:54:51.948Z"
    }
  ]
};

// Helper function to process the helix data into formatted memecoins
const processHelixData = (data: HelixCoin[]): FormattedMemecoin[] => {
  return data.map((coin, index) => {
    // Extract the coin name from the symbol (before the / if it exists)
    const symbolParts = coin.symbol.split('/');
    const name = symbolParts[0];
    
    const price = parsePrice(coin.price);
    
    return {
      id: index + 1,
      name,
      symbol: name,
      logo: '/trendpup-logo.png', // Default logo
      price,
      change24h: parseChange(coin.change_24h),
      marketCap: Math.round(price * 1000000 * (Math.random() * 5 + 1)), // Generate random market cap
      risk: calculateRisk(price, coin.change_24h),
      potential: calculatePotential(price, coin.change_24h),
      favorite: false,
      // Add the new detailed data fields if available
      marketId: coin.market_id,
      helixLink: coin.helix_link,
      tickSize: coin.tick_size,
      minOrderSize: coin.min_limit_order_size,
      high24h: parseNumericValue(coin.high_24h),
      low24h: parseNumericValue(coin.low_24h)
    };
  });
};

export const fetchHelixData = async (): Promise<FormattedMemecoin[]> => {
  try {
    const response = await fetch('/api/helix-data');
    
    if (!response.ok) {
      console.warn('API request failed, using fallback data');
      return processHelixData(fallbackData.data);
    }
    
    const data: HelixDataResponse = await response.json();
    return processHelixData(data.data);
  } catch (error) {
    console.error('Error fetching Helix data:', error);
    console.warn('Using fallback data due to error');
    return processHelixData(fallbackData.data);
  }
}; 