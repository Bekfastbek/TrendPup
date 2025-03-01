import secrets
from typing import Dict, Literal, Optional
from datetime import datetime
import os
import yaml
from pyinjective.wallet import PrivateKey

NetworkType = Literal["mainnet", "testnet"]


class AgentManager:
    """Manages multiple trading agents and their private keys"""

    def __init__(self, config_path: str = "agents_config.yaml"):
        self.config_path = config_path
        self.agents: Dict[str, dict] = self._load_agents()
        self.current_agent: Optional[str] = None
        self.current_network: NetworkType = "testnet"  # Default to testnet for safety

    def _load_agents(self) -> Dict[str, dict]:
        """Load agents from config file"""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _save_agents(self):
        """Save agents to config file"""
        with open(self.config_path, "w") as f:
            yaml.dump(self.agents, f)

    def switch_network(self, network: NetworkType):
        """Switch between mainnet and testnet"""
        if network.lower() not in ["mainnet", "testnet"]:
            raise ValueError("Network must be either 'mainnet' or 'testnet'")
        self.current_network = network.lower()

    def get_current_network(self) -> NetworkType:
        """Get current network"""
        return self.current_network

    def create_agent(self, name: str) -> dict:
        """Create a new agent with a private key"""
        if name in self.agents:
            raise ValueError(f"Agent '{name}' already exists")

        # Generate new private key
        private_key = str(secrets.token_hex(32))
        inj_pub_key = (
            PrivateKey.from_hex(private_key)
            .to_public_key()
            .to_address()
            .to_acc_bech32()
        )
        agent_info = {
            "private_key": private_key,
            "address": str(inj_pub_key),
            "created_at": datetime.now().isoformat(),
            "network": self.current_network,
        }

        self.agents[name] = agent_info
        self._save_agents()
        return agent_info

    def delete_agent(self, name: str):
        """Delete an existing agent"""
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not found")

        del self.agents[name]
        if self.current_agent == name:
            self.current_agent = None
        self._save_agents()

    def switch_agent(self, name: str):
        """Switch to a different agent"""
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not found")
        self.current_agent = name

    def get_current_agent(self) -> Optional[dict]:
        """Get current agent information"""
        if self.current_agent:
            return self.agents[self.current_agent]
        return None

    def list_agents(self) -> Dict[str, dict]:
        """List all available agents"""
        return self.agents

    def get_agent_based_on_network(self):
        testnet_agents, mainnet_agents = dict(), dict()
        for agent, value in self.agents.items():
            if value["network"] == "testnet":
                testnet_agents[agent] = value
            else:
                mainnet_agents[agent] = value
        return mainnet_agents, testnet_agents
