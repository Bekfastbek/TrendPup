import express from 'express';
import { elizaLogger } from '@elizaos/core';
import router from './routes.ts';

const app = express();
const PORT = process.env.API_PORT || 4000;
app.use('/api', router);

export const startServer = () => {
  app.listen(PORT, () => {
    elizaLogger.log(`API Server running on port ${PORT}`);
  });
};
