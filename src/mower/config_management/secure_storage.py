"""Secure storage for sensitive configuration data.

This module provides functions for securely storing and retrieving
sensitive configuration data such as API keys, passwords, etc.
"""

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from mower.utilities.logger_config import LoggerConfigInfo

# Initialize logger
logger = LoggerConfigInfo.get_logger(__name__)


class SecureStorage:
    """Secure storage for sensitive configuration data.

    This class provides methods for securely storing and retrieving
    sensitive configuration data such as API keys, passwords, etc.
    It uses Fernet symmetric encryption to encrypt the data.
    """

    def __init__(self, storage_path: Union[str, Path], master_key_env_var: str = 'MOWER_MASTER_KEY'):
        """Initialize the secure storage.

        Args:
            storage_path: Path to the secure storage file.
            master_key_env_var: Name of the environment variable containing the master key.
        """
        self.storage_path = Path(storage_path)
        self.master_key_env_var = master_key_env_var
        self._fernet = None
        self._data = {}
        
        # Create the directory if it doesn't exist
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize the encryption key
        self._initialize_key()
        
        # Load existing data if available
        self._load_data()

    def _initialize_key(self) -> None:
        """Initialize the encryption key.

        If the master key doesn't exist in the environment, a new one is generated
        and stored in a file. This is not ideal for production, but it's better
        than hardcoding the key or storing it in plaintext.
        """
        master_key = os.environ.get(self.master_key_env_var)
        
        if not master_key:
            # If no master key is found, generate one and store it
            key_file = self.storage_path.parent / '.master_key'
            
            if key_file.exists():
                # Read the key from the file
                with open(key_file, 'rb') as f:
                    master_key = f.read().decode('utf-8')
            else:
                # Generate a new key
                master_key = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
                
                # Store the key in a file with restricted permissions
                with open(key_file, 'wb') as f:
                    f.write(master_key.encode('utf-8'))
                
                # Set file permissions to be readable only by the owner
                os.chmod(key_file, 0o600)
                
                logger.info(f"Generated new master key and stored it in {key_file}")
            
            # Set the environment variable for future use
            os.environ[self.master_key_env_var] = master_key
        
        # Derive a key from the master key
        salt = b'autonomous_mower_salt'  # Fixed salt for consistency
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode('utf-8')))
        
        # Create the Fernet cipher
        self._fernet = Fernet(key)

    def _load_data(self) -> None:
        """Load data from the secure storage file."""
        if not self.storage_path.exists():
            self._data = {}
            return
            
        try:
            with open(self.storage_path, 'rb') as f:
                encrypted_data = f.read()
                
            if encrypted_data:
                decrypted_data = self._fernet.decrypt(encrypted_data)
                self._data = json.loads(decrypted_data.decode('utf-8'))
            else:
                self._data = {}
        except Exception as e:
            logger.error(f"Failed to load secure storage data: {e}")
            self._data = {}

    def _save_data(self) -> None:
        """Save data to the secure storage file."""
        try:
            data_json = json.dumps(self._data)
            encrypted_data = self._fernet.encrypt(data_json.encode('utf-8'))
            
            with open(self.storage_path, 'wb') as f:
                f.write(encrypted_data)
                
            # Set file permissions to be readable only by the owner
            os.chmod(self.storage_path, 0o600)
        except Exception as e:
            logger.error(f"Failed to save secure storage data: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the secure storage.

        Args:
            key: The key to retrieve.
            default: The default value to return if the key doesn't exist.

        Returns:
            The value associated with the key, or the default value if the key doesn't exist.
        """
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the secure storage.

        Args:
            key: The key to set.
            value: The value to store.
        """
        self._data[key] = value
        self._save_data()

    def delete(self, key: str) -> None:
        """Delete a value from the secure storage.

        Args:
            key: The key to delete.
        """
        if key in self._data:
            del self._data[key]
            self._save_data()

    def clear(self) -> None:
        """Clear all data from the secure storage."""
        self._data = {}
        self._save_data()

    def get_all(self) -> Dict[str, Any]:
        """Get all data from the secure storage.

        Returns:
            A dictionary containing all the data in the secure storage.
        """
        return self._data.copy()


# Singleton instance
_secure_storage_instance = None


def get_secure_storage(storage_path: Optional[Union[str, Path]] = None) -> SecureStorage:
    """Get the secure storage instance.

    Args:
        storage_path: Path to the secure storage file. If not provided,
            the default path is used.

    Returns:
        The secure storage instance.
    """
    global _secure_storage_instance
    
    if _secure_storage_instance is None:
        if storage_path is None:
            # Use default path
            config_dir = Path(os.environ.get('CONFIG_DIR', 'config'))
            storage_path = config_dir / 'secure_storage.enc'
            
        _secure_storage_instance = SecureStorage(storage_path)
        
    return _secure_storage_instance