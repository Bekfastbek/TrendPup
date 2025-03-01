from mistralai.client import MistralClient
import os
import traceback
from dotenv import load_dotenv
from quart import Quart, request, jsonify
from datetime import datetime
import argparse
from injective_functions.factory import InjectiveClientFactory
from injective_functions.utils.function_helper import (
    FunctionSchemaLoader,
    FunctionExecutor,
)
import json
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve
import aiohttp
import pandas as pd
from glob import glob
from quart_cors import cors

app = Quart(__name__)
app = cors(app, allow_origin = "http://localhost:7000")

class InjectiveChatAgent:
    def __init__(self):
        load_dotenv()

        self.api_key = os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No Mistral API key found. Please set the MISTRAL_API_KEY environment variable."
            )

        self.client = MistralClient(api_key = self.api_key)

        self.conversations = {}
        self.agents = {}
        schema_paths = [
            "./injective_functions/account/account_schema.json",
            "./injective_functions/auction/auction_schema.json",
            "./injective_functions/authz/authz_schema.json",
            "./injective_functions/bank/bank_schema.json",
            "./injective_functions/exchange/exchange_schema.json",
            "./injective_functions/staking/staking_schema.json",
            "./injective_functions/token_factory/token_factory_schema.json",
            "./injective_functions/utils/utils_schema.json",
        ]
        self.function_schemas = FunctionSchemaLoader.load_schemas(schema_paths)

    async def initialize_agent(
            self, agent_id: str, private_key: str, environment: str = "mainnet"
    ) -> None:
        if agent_id not in self.agents:
            clients = await InjectiveClientFactory.create_all(
                private_key = private_key, network_type = environment
            )
            self.agents[agent_id] = clients

    async def execute_function(
            self, function_name: str, arguments: dict, agent_id: str
    ) -> dict:
        try:
            # Get the client dictionary for this agent
            clients = self.agents.get(agent_id)
            if not clients:
                return {
                    "error": "Agent not initialized. Please provide valid credentials."
                }

            return await FunctionExecutor.execute_function(
                clients = clients, function_name = function_name, arguments = arguments
            )

        except Exception as e:
            return {
                "error": str(e),
                "success": False,
                "details": {"function": function_name, "arguments": arguments},
            }

    async def get_response(
            self,
            message,
            session_id = "default",
            private_key = None,
            agent_id = None,
            environment = "mainnet",
    ):
        await self.initialize_agent(
            agent_id = agent_id, private_key = private_key, environment = environment
        )
        print("initialized agents")
        try:
            if session_id not in self.conversations:
                self.conversations[session_id] = []

            self.conversations[session_id].append({"role": "user", "content": message})

            system_message = {
                "role": "system",
                "content": """You are a helpful AI assistant on Injective Chain. 
                You will be answering all things related to injective chain, and help out with
                on-chain functions.

                When handling market IDs, always use these standardized formats:
                - For BTC perpetual: "BTC/USDT PERP" maps to "btcusdt-perp"
                - For ETH perpetual: "ETH/USDT PERP" maps to "ethusdt-perp"

                When users mention markets:
                1. If they use casual terms like "Bitcoin perpetual" or "BTC perp", interpret it as "BTC/USDT PERP"
                2. If they mention "Ethereum futures" or "ETH perpetual", interpret it as "ETH/USDT PERP"
                3. Always use the standardized format in your responses

                Before performing any action:
                1. Describe what you're about to do
                2. Ask for explicit confirmation
                3. Only proceed after receiving a "yes"

                When making function calls:
                1. Convert the standardized format (e.g., "BTC/USDT PERP") to the internal format (e.g., "btcusdt-perp")
                2. When displaying results to users, convert back to the standard format
                3. Always confirm before executing any functions

                For general questions, provide informative responses.
                When users want to perform actions, describe the action and ask for confirmation but for fetching data you dont have to ask for confirmation."""
            }

            print("Preparing to send request to chat model...")
            print(f"Messages being sent: {[system_message] + self.conversations[session_id]}")
            print(f"Tools being sent: {self.function_schemas}")

            try:
                print("Sending request to chat model...")
                response = await asyncio.to_thread(
                    self.client.chat,
                    model = "mistral-large-latest",
                    messages = [system_message] + self.conversations[session_id],
                    tools = self.function_schemas,
                    tool_choice = "auto",
                    max_tokens = 2000,
                    temperature = 0.7,
                )
                print("Raw response received:", response)
                print("Response type:", type(response))
                print("Response attributes:", dir(response))

                if not hasattr(response, 'choices') or not response.choices:
                    raise ValueError("No choices in response")

                response_message = response.choices[0].message
                print("Response message:", response_message)
                print("Response message type:", type(response_message))
                print("Response message attributes:", dir(response_message))

                # Handle tool calls if they exist
                tool_calls = getattr(response_message, 'tool_calls', None)
                function_call = None

                if tool_calls:
                    print("Tool calls found:", tool_calls)
                    print("Tool calls type:", type(tool_calls))

                    if isinstance(tool_calls, list) and tool_calls:
                        tool_call = tool_calls[0]
                        print("First tool call:", tool_call)
                        print("Tool call attributes:", dir(tool_call))

                        function_call = {
                            "id": str(uuid.uuid4()),
                            "type": "function",
                            "function": {
                                "name": getattr(tool_call.function, 'name', 'unknown'),
                                "arguments": getattr(tool_call.function, 'arguments', '{}')
                            }
                        }

                        # Add function call to conversation history
                        self.conversations[session_id].append({
                            "role": "assistant",
                            "content": None,
                            "function_call": function_call
                        })

                # Handle regular message content
                content = getattr(response_message, 'content', None)
                if content:
                    self.conversations[session_id].append({
                        "role": "assistant",
                        "content": content
                    })

                # If we have either content or function call, return them
                if content or function_call:
                    return {
                        "response": content,
                        "function_call": function_call,
                        "session_id": session_id,
                    }

                # Default response if no content or function call
                default_response = "I'm here to help you with trading on Injective Chain. How can I assist you today?"
                self.conversations[session_id].append({
                    "role": "assistant",
                    "content": default_response
                })
                return {
                    "response": default_response,
                    "function_call": None,
                    "session_id": session_id,
                }

            except Exception as chat_error:
                print(f"Chat error details: {type(chat_error).__name__}: {str(chat_error)}")
                print(f"Chat error traceback: {traceback.format_exc()}")
                raise chat_error

        except Exception as e:
            print(f"Error details: {type(e).__name__}: {str(e)}")
            print(f"Full traceback: {traceback.format_exc()}")
            error_response = f"I apologize, but I encountered an error: {str(e)}. How else can I help you?"
            return {
                "response": error_response,
                "function_call": None,
                "session_id": session_id,
            }

    def clear_history(self, session_id = "default"):
        """Clear conversation history for a specific session."""
        if session_id in self.conversations:
            self.conversations[session_id].clear()

    def get_history(self, session_id = "default"):
        """Get conversation history for a specific session."""
        return self.conversations.get(session_id, [])

    def clear_history(self, session_id = "default"):
        """Clear conversation history for a specific session."""
        if session_id in self.conversations:
            self.conversations[session_id].clear()

    def get_history(self, session_id = "default"):
        """Get conversation history for a specific session."""
        return self.conversations.get(session_id, [])


agent = InjectiveChatAgent()


@app.route("/ping", methods = ["GET"])
async def ping():
    """Health check endpoint"""
    return jsonify(
        {"status": "ok", "timestamp": datetime.now().isoformat(), "version": "1.0.0"}
    )


@app.route("/chat", methods = ["POST"])
async def chat_endpoint():
    try:
        data = await request.get_json()
        print("Received data:", data)

        if not data or "message" not in data:
            return (
                jsonify(
                    {
                        "error": "No message provided",
                        "response": "Please provide a message to continue our conversation.",
                        "session_id": data.get("session_id", "default"),
                        "agent_id": data.get("agent_id", "default"),
                        "agent_key": data.get("agent_key", "default"),
                        "environment": data.get("environment", "testnet"),
                    }
                ),
                400,
            )

        session_id = data.get("session_id", "default")
        private_key = data.get("agent_key", "default")
        agent_id = data.get("agent_id", "default")

        response = await agent.get_response(
            data["message"], session_id, private_key, agent_id
        )

        return jsonify(response)
    except Exception as e:

        import traceback
        print(f"Error occurred: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Traceback: {traceback.format_exc()}")

        return (
            jsonify(
                {
                    "error": str(e),
                    "response": "I apologize, but I encountered an error. Please try again.",
                    "session_id": data.get("session_id", "default"),
                }
            ),
            500,
        )



@app.route("/history", methods = ["GET"])
async def history_endpoint():
    session_id = request.args.get("session_id", "default")
    return jsonify({"history": agent.get_history(session_id)})


@app.route("/clear", methods = ["POST"])
async def clear_endpoint():
    session_id = request.args.get("session_id", "default")
    agent.clear_history(session_id)
    return jsonify({"status": "success"})


def main():
    parser = argparse.ArgumentParser(description = "Run the chatbot API server")
    parser.add_argument("--port", type = int, default = 5000, help = "Port for API server")
    parser.add_argument("--host", default = "127.0.0.1", help = "Host for API server")
    parser.add_argument("--debug", action = "store_true", help = "Run in debug mode")
    args = parser.parse_args()

    config = Config()
    config.bind = [f"{args.host}:{args.port}"]
    config.debug = args.debug

    print(f"Starting API server on {args.host}:{args.port}")
    asyncio.run(serve(app, config))


if __name__ == "__main__":
    main()