import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from logging import Logger
from typing import Any

import httpx2
from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from yr_mcp.config import BASE_URL, USER_AGENT
