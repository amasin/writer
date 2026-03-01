# GSC Performance Agent Integration

## Overview

The `gsc_performance_agent.py` provides real-time (or cached) Google Search Console performance insights to all other agents in the pipeline. This enables data-driven content optimization based on actual search performance metrics.

## Architecture

```
[GSC Performance Agent]
        ↓ (performance metrics)
        ├→ [SEO Title Agent] - optimize titles for higher CTR
        ├→ [WordPress Writer] - align content with search demand
        ├→ [Proofreader] - score based on search intent alignment
        └→ [Publisher Agent] - uses final scores
```

## Data Flow

### Step 1: Fetch GSC Insights
```python
gsc_data = gsc_agent.analyze_site()
# Returns:
{
  "site_performance": {
    "clicks": 3867,
    "impressions": 73070,
    "ctr": 0.0438,
    "position": 9.87,
    "timestamp": "2026-03-01T21:10:26.879331"
  },
  "low_ctr_pages": ["url1", "url2"],
  "keyword_opportunities": ["opportunity1", "opportunity2"]
}
```

### Step 2: Pass to SEO Title Agent
**Method:** `generate_title(topic, gsc_data)`

Uses GSC insights to penalize shorter titles when site-wide CTR is low (< 2%), encouraging longer, more descriptive titles that improve CTR.

Example influence:
- Low CTR → favor comprehensive titles (50+ chars with power words)
- Keyword opportunities → incorporate trending search terms

### Step 3: Pass to WordPress Writer
**Method:** `write_article(topic, title, gsc_data)`

Incorporates semantic keywords from GSC queries and adjusts content structure based on search intent.

Example adjustments:
- Low CTR → enhance intro and hook quality
- High impression keywords → weighted keyword placement
- Keyword gaps → suggest content sections

### Step 4: Pass to Proofreader
**Method:** `proofread(article, gsc_data)`

Enhances scoring by:
- Checking search intent alignment
- Validating keyword placement matches top queries
- Assessing readability against user behavior metrics
- Scoring heading optimization for voice search

## Caching Strategy

To prevent excessive API calls, GSC agent caches responses in `data/gsc_cache.json`:

```json
{
  "site": { "clicks": ..., "impressions": ..., "ctr": ... },
  "page:url1": { "url": "url1", "clicks": ..., "impressions": ... },
  "queries:url1": ["query1", "query2", ...],
  ...
}
```

Cache is automatically persisted after each API call.

## Methods

### Core API Methods

**`authenticate_gsc() → bool`**
- Checks if GSC credentials (API key) are available
- Mocked in this implementation; real version uses OAuth2

**`fetch_site_performance() → Dict`**
- Returns aggregated site metrics (clicks, impressions, CTR, avg position)
- Caches under key 'site'

**`fetch_page_performance(url: str) → Dict`**
- Returns metrics for a specific page URL
- Caches under key `page:{url}`

**`fetch_top_queries(url: str) → List[str]`**
- Returns top search queries for a given page
- Caches under key `queries:{url}`

**`detect_low_ctr_pages() → List[str]`**
- Returns URLs with CTR < 2% (configurable threshold)
- Useful for identifying underperforming content

**`detect_keyword_opportunities() → List[str]`**
- Returns keywords where position is high but impressions are low
- Targets quick wins for content optimization

**`analyze_site() → Dict`**
- Convenience method aggregating multiple metrics
- Returns comprehensive site insights

### Message API

Agent communicates via A2A protocol:

**Request for site analysis:**
```python
msg = A2AMessage(
    sender="orchestrator",
    receiver="gsc_performance_agent",
    message_type=MessageType.REQUEST,
    payload={"request_type": "analyze_site"}
)
response = broker.send_message(msg)
gsc_data = response.payload.get("gsc_data")
```

**Request for page performance:**
```python
msg = A2AMessage(
    sender="some_agent",
    receiver="gsc_performance_agent",
    message_type=MessageType.REQUEST,
    payload={
        "request_type": "get_page_performance",
        "url": "https://site.com/page"
    }
)
```

## Integration Points

### In Orchestrator
```python
# Fetch GSC data first
gsc_msg = A2AMessage(...)
gsc_resp = broker.send_message(gsc_msg)
gsc_data = gsc_resp.payload.get("gsc_data")

# Pass to all downstream agents
seo_title = seo_agent.generate_title(topic, gsc_data)
content = wp_agent.write_article(topic, title, gsc_data)
final = proofreader.proofread(content, gsc_data)
```

### In SEO Title Agent
```python
def generate_title(self, topic: str, gsc_data: Dict = None) -> str:
    if gsc_data and gsc_data["site_performance"]["ctr"] < 0.02:
        # Penalize short titles, favor comprehensive ones
```

### In WordPress Writer
```python
def write_article(self, topic: str, title: str, gsc_data: Dict = None) -> str:
    content = self._generate_wordpress_content(title, topic)
    if gsc_data and gsc_data["site_performance"]["ctr"] < 0.02:
        # Add CTA or enhance intro
```

### In Proofreader
```python
def analyze_article(self, content: str, title: str, topic: str, 
                   gsc_data: Dict = None) -> Tuple[float, List[str]]:
    # ... scoring logic ...
    if gsc_data and gsc_data["site_performance"]["ctr"] < 0.02:
        suggestions.append("GSC data indicates low CTR...")
```

## Configuration

Optional environment variables:

```bash
GSC_API_KEY=<your_api_key>  # For OAuth authentication
```

If not set, agent will use mock data for demonstration.

## Real-World Deployment

For production use with real Google Search Console API:

1. **Setup OAuth2 credentials** in Google Cloud Console
2. **Call Google Search Console API v3**:
   ```
   GET https://www.googleapis.com/webmasters/v3/sites/{siteUrl}/searchanalytics/query
   ```
3. **Implement request throttling** to respect rate limits
4. **Refresh cache periodically** (e.g., daily)
5. **Handle API errors gracefully** with fallback caching

Example real API call:

```python
def fetch_site_performance_real(self) -> Dict:
    """Fetch real GSC data using OAuth2."""
    import google.auth
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    
    creds = service_account.Credentials.from_service_account_file(
        'credentials.json',
        scopes=['https://www.googleapis.com/auth/webmasters']
    )
    service = build('webmasters', 'v3', credentials=creds)
    
    response = service.searchanalytics().query(
        siteUrl='https://yourdomain.com',
        body={
            'startDate': '2026-02-01',
            'endDate': '2026-02-28',
            'dimensions': ['query', 'page'],
            'rows': 100
        }
    ).execute()
    
    return response
```

## Testing

Run the demo to see GSC integration:

```bash
python demo.py
```

Output will show:
1. GSC data fetched with performance metrics
2. SEO title optimized based on CTR
3. Article content informed by keyword opportunities
4. Proofreader suggestions enhanced with search intent
5. Final publish with all insights applied

Monitor `data/gsc_cache.json` to see cache accumulation across runs.
