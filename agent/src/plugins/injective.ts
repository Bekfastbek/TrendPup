import { injectivePlugin } from '@elizaos/plugin-injective';
import { settings } from '@elizaos/core';

// Configure the plugin with any custom settings
export const configureInjectivePlugin = () => {
  // You can add any custom configuration here
  return injectivePlugin;
};

export default configureInjectivePlugin;