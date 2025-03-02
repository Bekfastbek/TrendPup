import type { NextApiRequest, NextApiResponse } from 'next';
import { DirectClient } from "@elizaos/client-direct";
import character from "../../../../agent/characters/balance.character.json"; // Ensure this matches the expected structure
import { startAgent } from "../../../../agent/src/index"; // Ensure startAgent is exported

let directClient: DirectClient | null = null;

const initializeAgent = async () => {
  if (!directClient) {
    directClient = new DirectClient();
    await startAgent(character, directClient);
  }
};

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'POST') {
    const { message } = req.body;

    try {
      await initializeAgent();

      // Here you would send the message to the agent and get a response
      const response = await directClient?.startAgent(character); // Use optional chaining

      if (response) {
        res.status(200).json({ response });
      } else {
        res.status(500).json({ error: 'No res`ponse from agent' });
      }
    } catch (error) {
      res.status(500).json({ error: 'Error processing the message' });
    }
  } else {
    res.setHeader('Allow', ['POST']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}
