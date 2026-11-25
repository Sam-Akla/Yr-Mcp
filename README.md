# Yr MCP

Yr MCP is a local [Model Context Protocol](https://modelcontextprotocol.io/) server for weather data from the Norwegian Meteorological Institute (MET Norway). It gives MCP clients access to worldwide forecasts, short-term Nordic precipitation forecasts, weather alerts, and sun and moon events.

## Install

You’ll need [uv](https://docs.astral.sh/uv/), Python 3.13 or later, and an MCP client that supports `stdio`. Weather requests require internet access to `api.met.no`. The server does not require an API key.

From the project directory, install the dependencies from the lockfile:

```bash
uv sync --locked
```

## Connect an MCP client

The server runs over `stdio`, so your MCP client starts it as a subprocess. For clients that use an `mcpServers` JSON configuration, add this entry:

```json
{
  "mcpServers": {
    "yr-mcp": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/yr_mcp", "run", "yr-mcp"]
    }
  }
}
```

Replace `/absolute/path/to/yr_mcp` with the directory containing `pyproject.toml`. If your client cannot find `uv`, use the absolute path returned by `command -v uv` as the `command`. Reload the client after saving its configuration.

## Tools

All four tools take `latitude` and `longitude` in decimal degrees. Supply the coordinates when making a request. Place-name lookup is not exposed as an MCP tool.

| Tool | What it returns | Main options |
| --- | --- | --- |
| `get_location_forecast` | Up to nine days of weather forecasts for coordinates worldwide | `usage_method` accepts `compact` or `complete` and defaults to `complete`. Optional `altitude` is in meters. |
| `get_now_cast` | A two-hour forecast for locations in Norway, Sweden, Finland, and Denmark, useful for near-term precipitation | `usage_method` defaults to `complete`. Optional `altitude` is in meters. |
| `get_sun_moon_events` | Rise, set, and other sun or moon events for a given date | `date` is required in `YYYY-MM-DD` format. `usage_method` defaults to `sun` and also accepts `moon`. `offset` is optional. |
| `get_met_alerts` | MET Norway weather alerts | `sort` is required, for example `t_onset`. The defaults are `current` alerts, English (`en`), and the `land` domain. With `usage_method: "archive"`, provide `date` for a day or `period` for a month. Both inputs take `YYYY-MM-DD`, and the server uses only the year and month from `period`. |

The server also exposes a `travel_planner` prompt that takes a `destination` and asks the client to use the forecast to discuss travel conditions such as temperature, wind, and precipitation.

## Example

Ask your MCP client:

> Use Yr MCP to get the compact forecast for Oslo at latitude 59.9139 and longitude 10.7522. Summarize tomorrow’s temperature, wind, and precipitation.

To call `get_location_forecast` directly, use these arguments:

```json
{
  "latitude": 59.9139,
  "longitude": 10.7522,
  "usage_method": "compact"
}
```

## Smoke test

From the project directory, run:

```bash
uv run python test/simple_smoke_test.py
```
The script checks that the forecast tool is registered and calls it with coordinates for Oslo. It requires internet access.

## Roadmap

- [ ] Expose place-name and address lookup as an MCP tool so users can find coordinates for weather requests.
- [ ] Return actionable errors when MET Norway requests fail or return an unreadable response.
- [ ] Expand automated coverage for all four weather tools using mocked API responses, alongside the existing `stdio` startup check.
