import express, { Request, Response, Router } from 'express';
import cors from 'cors';
import { type Character } from '@elizaos/core';

const router = Router();
interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

const corsOptions = {
  origin: process.env.NEXT_PUBLIC_FRONTEND_URL || 'http://localhost:3000',
  credentials: true,
};

router.use(cors(corsOptions));
router.use(express.json());

router.get('/health', (req: Request, res: Response<ApiResponse>) => {
  res.json({ success: true, data: { status: 'healthy' } });
});

router.get('/agents', async (req: Request, res: Response<ApiResponse>) => {
  try {
    const agents = global.directClient?.getAgents() || [];
    res.json({
      success: true,
      data: agents.map(agent => ({
        id: agent.agentId,
        name: agent.character.name,
        status: 'active'
      }))
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to fetch agents'
    });
  }
});

router.post('/agents', async (req: Request, res: Response<ApiResponse>) => {
  try {
    const { character } = req.body;
    if (!character?.name) {
      return res.status(400).json({
        success: false,
        error: 'Invalid character configuration'
      });
    }

    const agent = await global.directClient?.startAgent(character);
    res.status(201).json({
      success: true,
      data: {
        id: agent.agentId,
        name: agent.character.name
      }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to create agent'
    });
  }
});

router.get('/agents/:id', async (req: Request, res: Response<ApiResponse>) => {
  try {
    const agent = global.directClient?.getAgent(req.params.id);
    if (!agent) {
      return res.status(404).json({
        success: false,
        error: 'Agent not found'
      });
    }
    res.json({
      success: true,
      data: {
        id: agent.agentId,
        name: agent.character.name,
        status: 'active'
      }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to fetch agent'
    });
  }
});

export default router;
