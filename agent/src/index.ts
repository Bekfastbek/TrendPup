import express from "express";
import { DirectClient } from "@elizaos/client-direct";
import {
  AgentRuntime,
  elizaLogger,
  settings,
  stringToUuid,
  type Character,
  type Plugin,
} from "@elizaos/core";
import { bootstrapPlugin } from "@elizaos/plugin-bootstrap";
import { createNodePlugin } from "@elizaos/plugin-node";
import { solanaPlugin } from "@elizaos/plugin-solana";
import { injectivePlugin } from "@elizaos/plugin-injective";

import fs from "fs";
import net from "net";
import path from "path";
import { fileURLToPath } from "url";
import { BalanceActions } from "./actions/balance-actions.ts";
import { initializeDbCache } from "./cache/index.ts";
import { character } from "./character.ts";
import { startChat } from "./chat/index.ts";
import { initializeClients } from "./clients/index.ts";
import {
  getTokenForProvider,
  loadCharacters,
  parseArguments,
} from "./config/index.ts";
import { initializeDatabase } from "./database/index.ts";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = settings.SERVER_PORT || 4000;
app.use(express.json());

const directClient = new DirectClient();
let nodePlugin: any | undefined;

export function createAgent(
  character: Character,
  db: any,
  cache: any,
  token: string
) {
  elizaLogger.success("Creating runtime for character", character.name);

  nodePlugin ??= createNodePlugin();
  const plugins: Plugin[] = [bootstrapPlugin, nodePlugin];

  if (character.settings?.secrets?.WALLET_PUBLIC_KEY) {
    plugins.push(solanaPlugin);
  }
  if (character.name === "InjectiveAssistant") {
    plugins.push(injectivePlugin);
    elizaLogger.debug("Added Injective plugin for InjectiveAssistant");
  }

  let actions = [];
  if (character.name === "InjectiveAssistant") {
    actions = BalanceActions;
  }

  return new AgentRuntime({
    databaseAdapter: db,
    token,
    modelProvider: character.modelProvider,
    evaluators: [],
    character,
    plugins,
    providers: [],
    actions,
    services: [],
    managers: [],
    cacheManager: cache,
  });
}

async function startAgent(character: Character) {
  try {
    character.id ??= stringToUuid(character.name);
    character.username ??= character.name;

    const token = getTokenForProvider(character.modelProvider, character);
    const dataDir = path.join(__dirname, "../data");

    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }

    const db = initializeDatabase(dataDir);
    await db.init();
    const cache = initializeDbCache(character, db);
    const runtime = createAgent(character, db, cache, token);
    await runtime.initialize();
    runtime.clients = await initializeClients(character, runtime);

    directClient.registerAgent(runtime);

    elizaLogger.debug(`Started ${character.name} as ${runtime.agentId}`);
    return runtime;
  } catch (error) {
    elizaLogger.error(`Error starting agent for ${character.name}:`, error);
    throw error;
  }
}

const startAgents = async () => {
  const args = parseArguments();
  let charactersArg = args.characters || args.character;
  let characters = [character];

  if (charactersArg) {
    characters = await loadCharacters(charactersArg);
  }

  try {
    for (const character of characters) {
      await startAgent(character);
    }
  } catch (error) {
    elizaLogger.error("Error starting agents:", error);
  }
};

// Express API Routes

// Health Check
app.get("/health", (req, res) => {
  res.json({ success: true, status: "Server is running" });
});

// Get all active agents
app.get("/agents", (req, res) => {
  const agents = directClient.getAgents() || [];
  res.json({
    success: true,
    data: agents.map((agent) => ({
      id: agent.agentId,
      name: agent.character.name,
      status: "active",
    })),
  });
});

// Start a new agent
app.post("/agents", async (req, res) => {
  try {
    const { character } = req.body;
    if (!character?.name) {
      return res.status(400).json({ success: false, error: "Invalid character" });
    }

    const agent = await startAgent(character);
    res.status(201).json({
      success: true,
      data: { id: agent.agentId, name: agent.character.name },
    });
  } catch (error) {
    res.status(500).json({ success: false, error: "Failed to create agent" });
  }
});

// Get a specific agent by ID
app.get("/agents/:id", (req, res) => {
  const agent = directClient.getAgent(req.params.id);
  if (!agent) {
    return res.status(404).json({ success: false, error: "Agent not found" });
  }
  res.json({
    success: true,
    data: { id: agent.agentId, name: agent.character.name, status: "active" },
  });
});

// Start Express Server
app.listen(PORT, () => {
  elizaLogger.log(`API Server running on port ${PORT}`);
});

// Start agents
startAgents().catch((error) => {
  elizaLogger.error("Unhandled error in startAgents:", error);
  process.exit(1);
});

export { startAgent };
