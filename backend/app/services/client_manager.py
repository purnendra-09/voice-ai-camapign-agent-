from typing import Dict, List, Optional, Any
import json
import os
from app.utils import get_logger

logger = get_logger(__name__)


class ClientManager:
    """Manages multi-client/hospital metadata and configuration"""

    def __init__(self):
        """Initialize client manager"""
        self.clients = {}
        self._load_clients_from_config()

    def _load_clients_from_config(self):
        """Load client configurations from clients_config.json"""
        try:
            # Get current working directory
            cwd = os.getcwd()
            logger.info(f"Current working directory: {cwd}")

            # Try to load from clients_config.json
            # Use absolute path to avoid issues with CWD
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(base_dir, "clients_config.json")
            
            logger.info(f"Attempting to load config from: {config_path}")
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                    # Handle nested structure if present
                    if "clients" in config_data and isinstance(config_data["clients"], dict):
                        self.clients = config_data["clients"]
                        logger.info("Detected nested 'clients' structure in config")
                    else:
                        self.clients = config_data
                
                logger.info(f"Loaded {len(self.clients)} clients from {config_path}")
                logger.info(f"Available clients: {list(self.clients.keys())}")
            else:
                logger.warning(f"clients_config.json not found at {config_path}. Loading defaults.")
                self._load_default_clients()

            # NEW: Check for individual client files in the base directory
            # This handles cases like akira_eye_hospital_amalapuram.json
            self._scan_for_individual_clients(base_dir)

        except Exception as e:
            logger.error(f"Error loading clients config: {str(e)}. Loading defaults.")
            import traceback
            logger.error(traceback.format_exc())
            self._load_default_clients()

    def _scan_for_individual_clients(self, base_dir: str):
        """Scan for individual client JSON files in the base directory"""
        try:
            logger.info(f"Scanning for individual client files in: {base_dir}")
            for filename in os.listdir(base_dir):
                if filename.endswith(".json") and filename != "clients_config.json" and filename != "prompts_config.json":
                    file_path = os.path.join(base_dir, filename)
                    client_id = filename.replace(".json", "")
                    
                    logger.info(f"Found potential client file: {filename} (ID: {client_id})")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            client_data = json.load(f)
                            if client_data:
                                # Standardize the data if it's in the special Akira format
                                standardized_data = self._standardize_client_data(client_data)
                                self.clients[client_id] = standardized_data
                                logger.info(f"Loaded and standardized client: {client_id}")
                    except Exception as e:
                        logger.warning(f"Could not load client file {filename}: {str(e)}")
        except Exception as e:
            logger.error(f"Error scanning for individual clients: {str(e)}")

    def _standardize_client_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert special hospital config format to standard client format"""
        # If it already has the standard layout, return as is
        if "name" in data and "location" in data:
            return data
            
        # If it has hospital_metadata, transform it
        metadata = data.get("hospital_metadata", {})
        operational = data.get("operational_config", {})
        
        return {
            "name": metadata.get("name", "Unknown Hospital"),
            "location": metadata.get("location", "Unknown Location"),
            "phone": metadata.get("phone", "XXXX-XXXX"),
            "hours": metadata.get("hours", "9 AM - 8 PM"),
            "specialties": metadata.get("specialties", []),
            "language": data.get("assistant_identity", {}).get("primary_language", "Telugu"),
            "timezone": operational.get("timezone", "IST"),
            "google_sheet_id": operational.get("google_sheet_id", "default"),
            "prompt_key": operational.get("prompt_key", "default"),
            "original_config": data # Keep original for tool specialized prompts if needed
        }

    def _load_default_clients(self):
        """Load default client configurations"""
        self.clients = {
            "default_hospital": {
                "name": "Default Hospital",
                "location": "City, State",
                "phone": "XXXX-XXXX",
                "hours": "9 AM - 8 PM",
                "specialties": ["General", "Cardiology", "Orthopedics"],
                "language": "Telugu",
                "timezone": "IST",
                "google_sheet_id": "default",
                "prompt_key": "default",
            }
        }

    def add_client(self, client_id: str, client_data: Dict[str, Any]) -> bool:
        """
        Add or update a client

        Args:
            client_id: Unique client identifier
            client_data: Client configuration dictionary

        Returns:
            True if successful
        """
        try:
            # Validate required fields
            required_fields = ["name", "location", "phone"]
            for field in required_fields:
                if field not in client_data:
                    logger.warning(f"Missing required field '{field}' for client {client_id}")

            self.clients[client_id] = client_data
            logger.info(f"Client added/updated: {client_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding client: {str(e)}")
            return False

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get client configuration

        Args:
            client_id: Client identifier

        Returns:
            Client configuration or None
        """
        return self.clients.get(client_id)

    def client_exists(self, client_id: str) -> bool:
        """
        Check if client exists

        Args:
            client_id: Client identifier

        Returns:
            True if exists
        """
        return client_id in self.clients

    def list_clients(self) -> List[str]:
        """
        List all client IDs

        Returns:
            List of client IDs
        """
        return list(self.clients.keys())

    def get_client_metadata(self, client_id: str) -> Dict[str, Any]:
        """
        Get client metadata

        Args:
            client_id: Client identifier

        Returns:
            Client metadata
        """
        client = self.get_client(client_id)
        if not client:
            logger.warning(f"Client not found: {client_id}")
            return {}

        return {
            "name": client.get("name", "Unknown"),
            "location": client.get("location"),
            "phone": client.get("phone"),
            "hours": client.get("hours"),
            "specialties": client.get("specialties", []),
            "language": client.get("language", "English"),
            "timezone": client.get("timezone", "UTC"),
            "prompt_key": client.get("prompt_key", "default"),
        }

    def get_client_sheet_id(self, client_id: str) -> Optional[str]:
        """
        Get Google Sheet ID for client

        Args:
            client_id: Client identifier

        Returns:
            Sheet ID or None
        """
        client = self.get_client(client_id)
        if not client:
            return None
        return client.get("google_sheet_id")

    def get_client_prompt_key(self, client_id: str) -> str:
        """
        Get prompt key for client

        Args:
            client_id: Client identifier

        Returns:
            Prompt key (default if not set)
        """
        client = self.get_client(client_id)
        if not client:
            return "default"
        return client.get("prompt_key", "default")

    def load_from_file(self, file_path: str) -> bool:
        """
        Load clients from JSON file

        Args:
            file_path: Path to JSON file with client configurations

        Returns:
            True if successful
        """
        try:
            import json

            with open(file_path, "r", encoding="utf-8") as f:
                clients = json.load(f)
                self.clients.update(clients)
                logger.info(f"Clients loaded from file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading clients from file: {str(e)}")
            return False

    def delete_client(self, client_id: str) -> bool:
        """
        Delete a client

        Args:
            client_id: Client identifier

        Returns:
            True if successful
        """
        try:
            if client_id in self.clients:
                del self.clients[client_id]
                logger.info(f"Client deleted: {client_id}")
                return True
            else:
                logger.warning(f"Client not found for deletion: {client_id}")
                return False
        except Exception as e:
            logger.error(f"Error deleting client: {str(e)}")
            return False
