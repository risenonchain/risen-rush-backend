from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class SecurityProvider(ABC):
    @abstractmethod
    async def scan(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        """
        Scans a contract or wallet address.
        Should return a standardized dictionary or None on failure.
        """
        pass
