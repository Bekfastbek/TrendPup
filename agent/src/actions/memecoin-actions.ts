import { AgentRuntime, Action } from "@elizaos/core";
import path from 'path';
import fs from 'fs';

// Path to the Twitter-scraper directory data files (relative to the agent directory)
const ANALYZED_MEMECOINS_PATH = path.resolve(process.cwd(), '../Twitter-scraper/coin_investment_analysis.json');

/**
 * Add memecoin-related actions to an Eliza agent
 */
export function addMemecoinActions(runtime: AgentRuntime) {
  for (const action of MemecoinActions) {
    runtime.registerAction(action);
  }
  console.log("Memecoin actions registered successfully");
}

/**
 * Get a textual risk level from a numeric score
 */
function getRiskLevel(score: number): string {
  if (!score) return 'Unknown';
  
  if (score >= 8) return 'Very High';
  if (score >= 6) return 'High';
  if (score >= 4) return 'Medium';
  if (score >= 2) return 'Low';
  return 'Very Low';
}

/**
 * Get a textual potential level from a numeric score
 */
function getPotentialLevel(score: number): string {
  if (!score) return 'Unknown';
  
  if (score >= 8) return 'Excellent';
  if (score >= 6) return 'Good';
  if (score >= 4) return 'Moderate';
  if (score >= 2) return 'Limited';
  return 'Poor';
}

/**
 * Read the memecoins data file
 */
async function readMemecoinsData() {
  try {
    const data = await fs.promises.readFile(ANALYZED_MEMECOINS_PATH, 'utf-8');
    return JSON.parse(data);
  } catch (error) {
    console.error('Error reading memecoin data:', error);
    throw error;
  }
}

/**
 * Get all available coins from the data file
 */
async function getAllCoins() {
  try {
    const data = await readMemecoinsData();
    if (!data || !data.coins || !Array.isArray(data.coins)) {
      return [];
    }
    return data.coins.map(coin => coin.symbol);
  } catch (error) {
    console.error('Error getting all coins:', error);
    return [];
  }
}

/**
 * Find coins in message by checking against available coins in the dataset
 */
async function findCoinsInMessage(text) {
  if (!text) return [];
  
  try {
    // Get all coins from our dataset
    const allCoins = await getAllCoins();
    if (!allCoins.length) return [];
    
    // Prepare text for comparison (uppercase)
    const upperText = text.toUpperCase();
    const foundCoins = [];
    
    // Check for each coin in our dataset
    for (const coin of allCoins) {
      if (upperText.includes(coin)) {
        foundCoins.push(coin);
      }
    }
    
    return foundCoins;
  } catch (error) {
    console.error('Error finding coins in message:', error);
    return [];
  }
}

// Trending memecoins action
const TrendingMemecoinsAction: Action = {
  name: "trendingMemecoins",
  description: "Get a list of trending memecoins from Twitter data",
  similes: ["get trending memecoins", "show top coins", "list popular tokens"],
  examples: [[
    { 
      user: "user", 
      content: { text: "What are the trending memecoins today?" }
    }
  ]],
  handler: async (runtime, message) => {
    const args = message.content.action ? JSON.parse(message.content.action) : {};
    const limit = args?.limit || 10;
    
    try {
      const data = await readMemecoinsData();
      if (!data || !data.coins || !Array.isArray(data.coins)) {
        return { text: 'No memecoin data available' };
      }
      
      // Sort by mention count and potential score
      const sortedData = data.coins.sort((a, b) => {
        // First sort by mention count
        const mentionDiff = (b.mention_count || 0) - (a.mention_count || 0);
        if (mentionDiff !== 0) return mentionDiff;
        
        // Then by potential score
        return (b.potential_score || 0) - (a.potential_score || 0);
      });
      
      // Limit and format the results
      const limitNum = parseInt(String(limit)) || 10;
      const trendingCoins = sortedData.slice(0, limitNum);
      
      // Format the response as readable text instead of JSON
      let response = `Here are the top ${trendingCoins.length} trending memecoins based on our analysis:\n\n`;
      
      trendingCoins.forEach((coin, index) => {
        response += `${index + 1}. **Coin:** ${coin.symbol}\n`;
        
        // Add market data from Coinbase if available
        if (coin.market_data) {
          response += `   * **Price:** $${coin.market_data.price_usd || 'N/A'}\n`;
          if (coin.market_data.price_change_24h_percent) {
            const change = parseFloat(coin.market_data.price_change_24h_percent);
            const changeSymbol = change >= 0 ? '↗️' : '↘️';
            response += `   * **24h Change:** ${changeSymbol} ${change}%\n`;
          }
          if (coin.market_data.volume_24h) {
            response += `   * **24h Volume:** $${coin.market_data.volume_24h}\n`;
          }
        }
        
        response += `   * **Risk Score:** ${coin.risk_score || 'N/A'}/10 (${getRiskLevel(coin.risk_score)})\n`;
        response += `   * **Potential Score:** ${coin.potential_score || 'N/A'}/10 (${getPotentialLevel(coin.potential_score)})\n`;
        response += `   * **Community Score:** ${coin.community_score || 'N/A'}/10\n`;
        response += `   * **Mention Count:** ${coin.mention_count || 0} times\n`;
        
        if (coin.red_flags && coin.red_flags.length > 0) {
          response += `   * **Key Risk:** ${coin.red_flags[0]}\n`;
        }
        
        if (coin.positive_indicators && coin.positive_indicators.length > 0) {
          response += `   * **Key Positive:** ${coin.positive_indicators[0]}\n`;
        }
        
        if (index < trendingCoins.length - 1) {
          response += '\n';
        }
      });
      
      response += '\nRemember, all memecoins are high-risk investments. Do your own research before investing.';
      
      return { text: response };
    } catch (error) {
      console.error('Error getting trending memecoins:', error);
      return { text: 'Failed to get trending coins' };
    }
  },
  validate: async (runtime, message) => {
    const text = (message?.content?.text || '').toLowerCase();
    return text.includes('trend') || text.includes('popular') || 
           text.includes('top') || text.includes('list');
  }
};

// Search memecoins action
const SearchMemecoinAction: Action = {
  name: "searchMemecoin",
  description: "Search for a specific memecoin by name or symbol",
  similes: ["find memecoin", "search for token", "lookup coin"],
  examples: [[
    {
      user: "user",
      content: { text: "Search for memecoin PEPE" }
    }
  ]],
  handler: async (runtime, message) => {
    const text = message.content.text || '';
    const args = message.content.action ? JSON.parse(message.content.action) : {};
    
    // Try to get coins mentioned in message
    const mentionedCoins = await findCoinsInMessage(text);
    
    // Check if action has query param or use the first mentioned coin
    const query = args?.query || (mentionedCoins.length > 0 ? mentionedCoins[0] : null);
    
    if (!query) {
      return { text: 'Please specify a coin to search for' };
    }
    
    try {
      const data = await readMemecoinsData();
      if (!data || !data.coins || !Array.isArray(data.coins)) {
        return { text: 'No memecoin data available' };
      }
      
      const searchTerm = query.toLowerCase();
      const results = data.coins.filter(coin => {
        const symbol = (coin.symbol || '').toLowerCase();
        return symbol.includes(searchTerm);
      });
      
      if (results.length === 0) {
        return { text: 'No memecoins found matching your search' };
      }
      
      // Format the response as readable text instead of JSON
      let response = `=== Search Results for "${query}" ===\n\n`;
      
      results.forEach((coin, index) => {
        response += `${index + 1}. **${coin.symbol}**\n`;
        response += `   • Mention Count: ${coin.mention_count || 0}\n`;
        response += `   • Risk Score: ${coin.risk_score || 'N/A'}/10 (${getRiskLevel(coin.risk_score)})\n`;
        response += `   • Potential Score: ${coin.potential_score || 'N/A'}/10 (${getPotentialLevel(coin.potential_score)})\n`;
        response += `   • Community Score: ${coin.community_score || 'N/A'}/10\n`;
        
        if (coin.red_flags && coin.red_flags.length > 0) {
          response += `   • Key Risk: ${coin.red_flags[0]}\n`;
        }
        
        if (coin.positive_indicators && coin.positive_indicators.length > 0) {
          response += `   • Key Positive: ${coin.positive_indicators[0]}\n`;
        }
        
        response += `   • Recommendation: ${coin.recommendation || 'No recommendation available'}\n`;
        
        if (index < results.length - 1) {
          response += '\n';
        }
      });
      
      return { text: response };
    } catch (error) {
      console.error('Error searching memecoins:', error);
      return { text: 'Failed to search for coins' };
    }
  },
  validate: async (runtime, message) => {
    const text = (message?.content?.text || '').toLowerCase();
    // Check for words indicating search intent
    return text.includes('search') || text.includes('find') || 
           text.includes('lookup') || text.includes('get info');
  }
};

// Coin info action
const MemecoinInfoAction: Action = {
  name: "memecoinInfo",
  description: "Get detailed information about a specific memecoin",
  similes: ["get coin details", "show memecoin info", "coin analysis", "info about"],
  examples: [[
    {
      user: "user",
      content: { text: "Tell me about DOGE coin" }
    }
  ]],
  handler: async (runtime, message) => {
    const text = message.content.text || '';
    const args = message.content.action ? JSON.parse(message.content.action) : {};
    
    // Try to get coins mentioned in message
    const mentionedCoins = await findCoinsInMessage(text);
    
    // Check if action has symbol param or use the first mentioned coin
    const symbol = args?.symbol || (mentionedCoins.length > 0 ? mentionedCoins[0] : null);
    
    if (!symbol) {
      return { text: 'Please specify a coin symbol to get information about' };
    }
    
    try {
      const data = await readMemecoinsData();
      if (!data || !data.coins || !Array.isArray(data.coins)) {
        return { text: 'No memecoin data available' };
      }
      
      const coin = data.coins.find(c => 
        c.symbol?.toLowerCase() === symbol.toLowerCase()
      );
      
      if (!coin) {
        return { text: `No data found for coin: ${symbol}` };
      }
      
      // Format the response as plain text instead of JSON
      const response = `
=== ${coin.symbol} Detailed Information ===

Basic Information:
• Symbol: ${coin.symbol}
• Mention Count: ${coin.mention_count || 0}
• First Seen: ${new Date(coin.first_seen).toLocaleString()}
• Latest Seen: ${new Date(coin.latest_seen).toLocaleString()}
• Categories: ${coin.categories?.join(', ') || 'None'}

${coin.market_data ? `Market Data:
• Price: $${coin.market_data.price_usd || 'N/A'}
• 24h Volume: $${coin.market_data.volume_24h || 'N/A'}
• 24h Price Change: ${coin.market_data.price_change_24h_percent || 'N/A'}%
• 24h High: $${coin.market_data.high_24h || 'N/A'}
• 24h Low: $${coin.market_data.low_24h || 'N/A'}
` : ''}
Analysis:
• Risk Score: ${coin.risk_score || 'N/A'}/10 (${getRiskLevel(coin.risk_score)})
• Potential Score: ${coin.potential_score || 'N/A'}/10 (${getPotentialLevel(coin.potential_score)})
• Community Score: ${coin.community_score || 'N/A'}/10

Risk Factors:
• Red Flags: ${coin.red_flags?.length ? '\n  - ' + coin.red_flags.join('\n  - ') : 'None identified'}
• Positive Indicators: ${coin.positive_indicators?.length ? '\n  - ' + coin.positive_indicators.join('\n  - ') : 'None identified'}

Community Links:
• Telegram Links: ${coin.telegram_links?.length ? '\n  - ' + coin.telegram_links.join('\n  - ') : 'None available'}
• Other Links: ${coin.other_links?.length ? '\n  - ' + coin.other_links.join('\n  - ') : 'None available'}

Recent Conversation:
${coin.sample_tweets?.length ? '• ' + coin.sample_tweets.join('\n• ') : 'No recent conversations found'}

Recommendation:
${coin.recommendation || 'No specific recommendation available for this coin'}
      `.trim();
      
      return { text: response };
    } catch (error) {
      console.error('Error getting coin info:', error);
      return { text: 'Failed to get coin information' };
    }
  },
  validate: async (runtime, message) => {
    const text = (message?.content?.text || '').toLowerCase();
    
    // First check if message mentions any known coins
    const mentionedCoins = await findCoinsInMessage(text);
    if (mentionedCoins.length === 0) return false;
    
    // Check if asking for information about a coin
    return text.includes('about') || text.includes('tell me') || 
           text.includes('what is') || text.includes('info');
  }
};

// Risk assessment action
const RiskAssessmentAction: Action = {
  name: "assessCoinRisk",
  description: "Get risk assessment and investment potential for a specific memecoin",
  similes: ["assess risk", "evaluate token", "check coin safety", "investment potential"],
  examples: [[
    {
      user: "user",
      content: { text: "What's the risk level of investing in PEPE?" }
    }
  ]],
  handler: async (runtime, message) => {
    const text = message.content.text || '';
    const args = message.content.action ? JSON.parse(message.content.action) : {};
    
    // Try to get coins mentioned in message
    const mentionedCoins = await findCoinsInMessage(text);
    
    // Check if action has symbol param or use the first mentioned coin
    const symbol = args?.symbol || (mentionedCoins.length > 0 ? mentionedCoins[0] : null);
    
    if (!symbol) {
      return { text: 'Please specify a coin symbol for risk assessment' };
    }
    
    try {
      const data = await readMemecoinsData();
      if (!data || !data.coins || !Array.isArray(data.coins)) {
        return { text: 'No memecoin data available' };
      }
      
      const coin = data.coins.find(c => 
        c.symbol?.toLowerCase() === symbol.toLowerCase()
      );
      
      if (!coin) {
        return { text: `No data found for coin: ${symbol}` };
      }
      
      // Format the response as plain text instead of JSON
      const response = `
=== ${coin.symbol} Analysis Report ===

Basic Information:
• Mention Count: ${coin.mention_count || 0}
• First Seen: ${new Date(coin.first_seen).toLocaleString()}
• Latest Seen: ${new Date(coin.latest_seen).toLocaleString()}
• Categories: ${coin.categories?.join(', ') || 'None'}
• Search Terms: ${coin.search_terms?.join(', ') || 'None'}

${coin.market_data ? `Market Data (from Coinbase):
• Price: $${coin.market_data.price_usd || 'N/A'}
• 24h Volume: $${coin.market_data.volume_24h || 'N/A'}
• 24h Price Change: ${coin.market_data.price_change_24h_percent || 'N/A'}%
• 24h High: $${coin.market_data.high_24h || 'N/A'}
• 24h Low: $${coin.market_data.low_24h || 'N/A'}
` : ''}
Risk Assessment:
• Risk Score: ${coin.risk_score || 'N/A'}/10 (${getRiskLevel(coin.risk_score)})
• Potential Score: ${coin.potential_score || 'N/A'}/10 (${getPotentialLevel(coin.potential_score)})
• Community Score: ${coin.community_score || 'N/A'}/10

Community & Links:
• Telegram Links: ${coin.telegram_links?.length ? coin.telegram_links.join(', ') : 'None'}
• Other Links: ${coin.other_links?.length ? coin.other_links.join(', ') : 'None'}

Risk Factors:
• Red Flags: ${coin.red_flags?.length ? '\n  - ' + coin.red_flags.join('\n  - ') : 'None'}
• Positive Indicators: ${coin.positive_indicators?.length ? '\n  - ' + coin.positive_indicators.join('\n  - ') : 'None'}

Sample Tweets:
${coin.sample_tweets?.length ? coin.sample_tweets.map(tweet => `• ${tweet}`).join('\n') : 'No sample tweets available'}

Final Recommendation:
${coin.recommendation || 'No recommendation available'}

Data Freshness:
• Last Updated: ${new Date(data.analysis_timestamp).toLocaleString()}
• Total Coins Analyzed: ${data.total_coins_analyzed}
      `.trim();
      
      return { text: response };
    } catch (error) {
      console.error('Error getting risk assessment:', error);
      return { text: 'Failed to assess coin risk' };
    }
  },
  validate: async (runtime, message) => {
    const text = (message?.content?.text || '').toLowerCase();
    
    // First check if message mentions any known coins
    const mentionedCoins = await findCoinsInMessage(text);
    if (mentionedCoins.length === 0) return false;
    
    // Check for risk/investment related intent
    return text.includes('risk') || text.includes('invest') || 
           text.includes('safe') || text.includes('buy') ||
           text.includes('potential') || text.includes('should');
  }
};

// Data freshness action
const MemecoinDataFreshnessAction: Action = {
  name: "memecoinDataFreshness",
  description: "Check when the memecoin data was last updated",
  similes: ["check data freshness", "when was data updated", "data update time"],
  examples: [[
    {
      user: "user",
      content: { text: "When was the memecoin data last updated?" }
    }
  ]],
  handler: async () => {
    try {
      const stats = await fs.promises.stat(ANALYZED_MEMECOINS_PATH);
      const lastUpdated = stats.mtime;
      const now = new Date();
      const diffMinutes = Math.floor((now.getTime() - lastUpdated.getTime()) / (1000 * 60));
      
      // Format as readable time period
      let timeAgo;
      if (diffMinutes < 60) {
        timeAgo = `${diffMinutes} minutes ago`;
      } else if (diffMinutes < 1440) {
        const hours = Math.floor(diffMinutes / 60);
        timeAgo = `${hours} hour${hours > 1 ? 's' : ''} ago`;
      } else {
        const days = Math.floor(diffMinutes / 1440);
        timeAgo = `${days} day${days > 1 ? 's' : ''} ago`;
      }
      
      // Format the response as plain text instead of JSON
      const response = `
=== Memecoin Data Freshness Report ===

• Data Last Updated: ${lastUpdated.toLocaleString()}
• Data Age: ${timeAgo}
• Status: ${diffMinutes < 180 ? '✅ Recent data' : '⚠️ Data might be outdated'}

Note: We strive to keep our memecoin data as fresh as possible. Data is typically updated every 1-2 hours to reflect the latest market and social media trends.
      `.trim();
      
      return { text: response };
    } catch (error) {
      console.error('Error checking data freshness:', error);
      return { text: 'Failed to check data freshness' };
    }
  },
  validate: async (runtime, message) => {
    const text = (message?.content?.text || '').toLowerCase();
    return text.includes('updated') || text.includes('freshness') || 
           text.includes('latest data') || text.includes('when was');
  }
};

// Export all memecoin actions
export const MemecoinActions = [
  TrendingMemecoinsAction,
  SearchMemecoinAction,
  MemecoinInfoAction,
  RiskAssessmentAction,
  MemecoinDataFreshnessAction
]; 