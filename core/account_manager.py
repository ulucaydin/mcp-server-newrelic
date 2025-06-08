from typing import Optional, Dict, Any
import os
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


class AccountManager:
    """Manages New Relic account credentials and switching"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the account manager
        
        Args:
            config_path: Path to accounts configuration file
        """
        self.config_path = config_path or Path.home() / ".newrelic-mcp" / "accounts.yaml"
        self.current_account: Optional[str] = None
        self._accounts: Dict[str, Dict[str, Any]] = {}
        self._load_accounts()
    
    def _load_accounts(self):
        """Load accounts from config file"""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    config = yaml.safe_load(f) or {}
                    self._accounts = config.get("accounts", {})
                    self.current_account = config.get("default")
                    
                    # Expand environment variables in API keys
                    for account_name, account_config in self._accounts.items():
                        if "api_key" in account_config:
                            api_key = account_config["api_key"]
                            # Check if it's an environment variable reference
                            if api_key.startswith("${") and api_key.endswith("}"):
                                env_var = api_key[2:-1]
                                account_config["api_key"] = os.getenv(env_var, "")
                                if not account_config["api_key"]:
                                    logger.warning(f"Environment variable {env_var} not set for account {account_name}")
                    
                    logger.info(f"Loaded {len(self._accounts)} accounts from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load accounts from {self.config_path}: {e}")
        else:
            logger.info(f"No accounts file found at {self.config_path}")
    
    def _save_accounts(self):
        """Save accounts to config file"""
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config = {
                "default": self.current_account,
                "accounts": self._accounts
            }
            
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
                
            logger.info(f"Saved accounts to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save accounts: {e}")
            raise
    
    def add_account(self, name: str, api_key: str, account_id: str, 
                   region: str = "US", set_default: bool = False):
        """Add or update an account configuration
        
        Args:
            name: Account name/alias
            api_key: New Relic API key
            account_id: New Relic account ID
            region: Region (US or EU)
            set_default: Whether to set as default account
        """
        self._accounts[name] = {
            "api_key": api_key,
            "account_id": account_id,
            "region": region,
            "nerdgraph_url": f"https://api.{'eu.' if region == 'EU' else ''}newrelic.com/graphql"
        }
        
        if set_default or not self.current_account:
            self.current_account = name
        
        self._save_accounts()
        logger.info(f"Added account: {name} (region: {region})")
    
    def remove_account(self, name: str):
        """Remove an account
        
        Args:
            name: Account name to remove
        """
        if name in self._accounts:
            del self._accounts[name]
            if self.current_account == name:
                # Set a new default if we removed the current one
                self.current_account = next(iter(self._accounts), None)
            self._save_accounts()
            logger.info(f"Removed account: {name}")
        else:
            raise ValueError(f"Account not found: {name}")
    
    def switch_account(self, name: str) -> Dict[str, Any]:
        """Switch to a different account
        
        Args:
            name: Account name to switch to
            
        Returns:
            Dictionary with account credentials
        """
        if name not in self._accounts:
            raise ValueError(f"Unknown account: {name}")
        self.current_account = name
        logger.info(f"Switched to account: {name}")
        # Emit event for session manager to clear caches
        return self.get_current_credentials()
    
    def get_current_credentials(self) -> Dict[str, Any]:
        """Get credentials for current account
        
        Returns:
            Dictionary with api_key, account_id, and nerdgraph_url
        """
        if not self.current_account:
            # Try environment variables as fallback
            api_key = os.getenv("NEW_RELIC_API_KEY")
            if api_key:
                return {
                    "api_key": api_key,
                    "account_id": os.getenv("NEW_RELIC_ACCOUNT_ID"),
                    "region": os.getenv("NEW_RELIC_REGION", "US"),
                    "nerdgraph_url": os.getenv("NEW_RELIC_NERDGRAPH_URL", 
                                              "https://api.newrelic.com/graphql")
                }
            raise ValueError("No account configured. Set NEW_RELIC_API_KEY environment variable or configure accounts.")
        
        return self._accounts[self.current_account]
    
    def list_accounts(self) -> Dict[str, Dict[str, Any]]:
        """List all configured accounts
        
        Returns:
            Dictionary of account configurations (with API keys masked)
        """
        result = {}
        for name, config in self._accounts.items():
            # Mask API keys for security
            masked_config = config.copy()
            if "api_key" in masked_config:
                api_key = masked_config["api_key"]
                if len(api_key) > 8:
                    masked_config["api_key"] = api_key[:4] + "..." + api_key[-4:]
                else:
                    masked_config["api_key"] = "***"
            masked_config["is_current"] = (name == self.current_account)
            result[name] = masked_config
        return result