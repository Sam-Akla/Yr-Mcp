from typing import Any

import httpx2
from mcp.server import MCPServer
from mcp.server.mcpserver import Context


async def make_weather_request(
    client: httpx2.AsyncClient, endpoint: str, params: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    try:
        response = await client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    except (httpx2.HTTPError, ValueError):
        return None


@mcp.tool(
    title="Get weather forecast",
    description="Get weather forecast from a specific location giving by the user",
)
async def get_weather(
    longitude: float, latitude: float, ctx: Context[AppContext]
) -> dict[str, Any] | None:
    client = ctx.request_context.lifespan_context.http_client

    logger.info("Fetching weather forecast")
    return await make_weather_request(
        client=client,
        endpoint="/weatherapi/locationforecast/2.0/compact",
        params={"lat": round(latitude, 4), "lon": round(longitude, 4)},
    )
