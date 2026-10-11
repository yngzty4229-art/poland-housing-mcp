# Poland Housing MCP – apartment valuation and real transaction prices for AI assistants

An [MCP](https://modelcontextprotocol.io/) server that gives Claude, ChatGPT, Cursor and other AI assistants
**official Polish housing-market data**:

- **what an apartment is worth** – an automated valuation (AVM) from comparable sales in notarial deeds,
- **what buyers actually paid** around any address – from Poland's Real Estate Price Register
  (*Rejestr Cen Nieruchomości*, RCN, notarial deeds, public since 13 February 2026),
- **what developers ask today** – from the price lists they must publish every day on dane.gov.pl,
- **the gap** between asking prices and real deed prices.

No scraping of listing portals: only official registers.

## Tools

| Tool | What it returns | Cost per call* |
|---|---|---|
| `value_apartment` | Estimated value and price per m² (PLN), value range, confidence, the most similar sales | ~0.49 USD |
| `transaction_prices` | Median price per m², quartiles, quarterly trend, primary vs resale, year-on-year change, individual deeds | ~0.25 USD + 0.003 USD per deed |
| `new_build_prices` | Developers' asking prices around an address: median per m², offers, investments | ~0.20 USD + 0.002 USD per offer |
| `asking_vs_deed_gap` | Asking prices vs prices paid in deeds, gap in %, by apartment size | ~0.49 USD |

\* Each tool runs a pay-per-event Actor on **your** [Apify](https://apify.com) account. The free Apify plan includes
monthly credit, so you can try every tool without paying. Nothing is charged when a location has no data.

## Setup

1. Create a free Apify account and copy your API token: **Apify Console → Settings → API & Integrations**.
2. Install [uv](https://docs.astral.sh/uv/) (it provides the `uvx` command).
3. Add the server to your MCP client.

**Claude Desktop** (`claude_desktop_config.json`), **Cursor** (`~/.cursor/mcp.json`) and most other clients:

```json
{
  "mcpServers": {
    "poland-housing": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/yngzty4229-art/poland-housing-mcp", "poland-housing-mcp"],
      "env": { "APIFY_TOKEN": "your_apify_token" }
    }
  }
}
```

**Claude Code:**

```bash
claude mcp add poland-housing --env APIFY_TOKEN=your_apify_token -- uvx --from git+https://github.com/yngzty4229-art/poland-housing-mcp poland-housing-mcp
```

Prefer nothing to install? The same tools are available as a hosted server through Apify (OAuth sign-in):
`https://mcp.apify.com?tools=kris_fili/poland-apartment-valuation,kris_fili/poland-real-estate-transaction-prices,kris_fili/poland-new-build-apartment-prices,kris_fili/poland-housing-price-gap`

## Example questions

- *How much is a 54 m² two-room flat at Długa 12 in Kraków worth?*
- *What did apartments sell for within 1 km of Puławska 100 in Warsaw over the last two years?*
- *How much more do developers in Gdańsk ask today than buyers paid in recent new-build deeds?*
- *Compare the median price per m² in notarial deeds in Wrocław and Poznań.*

Locations must be in Poland. Use Polish characters (`Łódź, Piotrkowska 100`) or coordinates (`50.06, 19.94`).

## Data and methodology

- Notarial deeds: Rejestr Cen Nieruchomości – Główny Urząd Geodezji i Kartografii (official bulk export + live service).
  Market sales of full ownership only; implausible prices removed. Counties publish with a delay of weeks to months –
  every result shows the newest deed used.
- Developers' asking prices: official daily price lists on dane.gov.pl.
- No personal data: the register contains no names of buyers or sellers.
- The valuation is an automated estimate (AVM), not a formal appraisal by a licensed valuer.

Weekly open statistics for the largest cities (CSV, CC BY 4.0):
[poland-housing-prices](https://github.com/yngzty4229-art/poland-housing-prices).
The underlying Actors: [apify.com/kris_fili](https://apify.com/kris_fili).

## License

Code: MIT.
