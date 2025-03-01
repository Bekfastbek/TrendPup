interface ChatRequest {
  message: string;
  session_id?: string;
  agent_id?: string;
  agent_key?: string;
  environment?: string;
}

interface ChatResponse {
  response: string;
  function_call: any;
  session_id: string;
}

export const endpoints = {
  async sendMessage(data: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await fetch('http://localhost:5000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      return await response.json();
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  },

  async getHistory(sessionId: string = 'default'): Promise<any> {
    try {
      const response = await fetch(`http://localhost:5000/history?session_id=${sessionId}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching history:', error);
      throw error;
    }
  },

  async clearHistory(sessionId: string = 'default'): Promise<any> {
    try {
      const response = await fetch(`http://localhost:5000/clear?session_id=${sessionId}`, {
        method: 'POST',
      });
      return await response.json();
    } catch (error) {
      console.error('Error clearing history:', error);
      throw error;
    }
  },
};