import express from "express";
import { startAgent } from "./src/index.ts";
import { DirectClient } from "@elizaos/client-direct";
import { loadCharacters } from "./config/index.ts";

const app = express();
const port = process.env.PORT || 4000;
const directClient = new DirectClient();

app.use(express.json());

// Start a specific agent
app.post("/start-agent", async (req, res) => {
  try {
    const { characterName } = req.body;
    if (!characterName) {
      return res.status(400).json({ error: "Character name is required" });
    }

    const characters = await loadCharacters(characterName);
    if (characters.length === 0) {
      return res.status(404).json({ error: "Character not found" });
    }

    const character = characters[0];
    const agent = await startAgent(character, directClient);
    res.json({ message: "Agent started successfully", agentId: agent.agentId });
  } catch (error) {
    res.status(500).json({ error: "Failed to start agent", details: error.message });
  }
});

// Get status of running agents
app.get("/agents", (req, res) => {
  const agents = directClient.getAgents();
  res.json(agents.map(agent => ({ agentId: agent.agentId, name: agent.character.name })));
});

// Stop an agent
app.post("/stop-agent", async (req, res) => {
  try {
    const { agentId } = req.body;
    if (!agentId) {
      return res.status(400).json({ error: "Agent ID is required" });
    }

    const agent = directClient.getAgentById(agentId);
    if (!agent) {
      return res.status(404).json({ error: "Agent not found" });
    }

    await agent.shutdown();
    res.json({ message: "Agent stopped successfully" });
  } catch (error) {
    res.status(500).json({ error: "Failed to stop agent", details: error.message });
  }
});

// Start the API server
app.listen(port, () => {
  console.log(`Agent API server is running on port ${port}`);
});
