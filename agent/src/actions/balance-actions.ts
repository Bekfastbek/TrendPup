import { Action, HandlerCallback, IAgentRuntime, elizaLogger } from '@elizaos/core';
import { ChainGrpcBankApi } from '@injectivelabs/sdk-ts';
import { BigNumberInBase } from '@injectivelabs/utils';
import { bech32 } from 'bech32';

function isValidInjectiveAddress(address: string): boolean {
    try {
        const { prefix } = bech32.decode(address);
        return prefix === 'inj';
    } catch (error) {
        return false;
    }
}

function extractInjectiveAddress(text: string): string | null {
    const addressRegex = /inj1[a-z0-9]{38}/g;
    const matches = text.match(addressRegex);

    if (matches && matches.length > 0) {
        if (isValidInjectiveAddress(matches[0])) {
            return matches[0];
        }
    }
    return null;
}

const MAX_RETRIES = 3; // Maximum number of retries
const RETRY_DELAY = 1000; // Delay between retries in milliseconds

/**
 * Check the balance of a specified Injective account
 */
export const CheckBalanceAction: Action = {
    name: 'CHECK_BALANCE',
    description: 'Check the balance of a specified Injective account',
    examples: [
        [
            {
                user: 'user',
                content: { text: 'What is my balance?' }
            },
            {
                user: 'InjectiveAssistant',
                content: { text: 'Please provide your Injective account address.' }
            }
        ],
        [
            {
                user: 'user',
                content: { text: 'What is the balance of inj14tf02w7tpw8z7fcz6ju8xvhmaategcdna2mrqc?' }
            },
            {
                user: 'InjectiveAssistant',
                content: { text: 'Retrieving the balance for account inj14tf02w7tpw8z7fcz6ju8xvhmaategcdna2mrqc...' }
            }
        ]
    ],
    similes: ["check wallet", "get balance", "view funds", "see tokens"],
    validate: async (runtime, message) => {
        const text = message?.content?.text?.toLowerCase() || '';
        return text.includes('balance');
    },
    handler: async (runtime: IAgentRuntime, message, state, options, callback?: HandlerCallback) => {
        try {
            if (!callback) return false;

            const userInput = message?.content?.text?.trim();
            const extractedAddress = extractInjectiveAddress(userInput);
            let address: string | null = extractedAddress;

            if (!address) {
                await callback({
                    text: 'Invalid Injective account address provided. Please provide a valid Injective address (starting with "inj1").',
                    content: {}
                });
                return false;
            }

            await callback({
                text: `Retrieving the balance for account ${address}...`,
                content: null
            });

            elizaLogger.debug(`Fetching balance for address: ${address}`);

            // Retry mechanism
            let retries = 0;
            while (retries < MAX_RETRIES) {
                try {
                    // Construct the ChainGrpcBankApi instance directly
                    const injectiveNetwork = runtime.getSetting("INJECTIVE_NETWORK");
                    const bankApi = new ChainGrpcBankApi(injectiveNetwork);

                    const balanceResponse = await bankApi.fetchBalance({ accountAddress: address, denom: 'inj' });

                    if (!balanceResponse) {
                        throw new Error("Invalid response structure from the balance API.");
                    }

                    const balanceAmount = new BigNumberInBase(balanceResponse.amount).dividedBy(10 ** 18).toFixed(6);

                    // Create the final response string (no LLM needed)
                    const responseText = `Your balance for account ${address} is: ${balanceAmount} INJ.`;

                    await callback({
                        text: responseText, //Use template response
                        content: {
                            accountAddress: address,
                            denom: 'inj',
                            amount: balanceAmount // include amount here
                        }
                    });

                    return true; // Success, exit the retry loop
                } catch (error: any) {
                    elizaLogger.error(`Error fetching balance (attempt ${retries + 1}): ${error.message}`);
                    retries++;

                    if (retries === MAX_RETRIES) {
                        //Last retry, so display a different message
                        await callback({
                            text: `There was an error retrieving the balance after multiple attempts. Please ensure the Injective API is accessible and try again later.`,
                            content: {}
                        });
                        return false; // Failed after all retries
                    }

                    // Wait before retrying
                    await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
                }
            }

            return false; // Should not reach here, but added for safety
        } catch (error) {
            elizaLogger.error(`Error fetching balance for ${message?.content?.text}: ${error.message}`);
            await callback({
                text: `There was an unexpected error retrieving the balance. Please try again later.`,
                content: {}
            });
            return false;
        }
    }
};

// Export all actions
export const BalanceActions = [
    CheckBalanceAction,
    //GetAccountInfoAction, // Remove this for now
    //GetTransactionHistoryAction
];