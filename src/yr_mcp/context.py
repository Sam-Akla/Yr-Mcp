from dataclasses import dataclass

import httpx2


@dataclass
class AppContext:
    http_client: httpx2.AsyncClient
