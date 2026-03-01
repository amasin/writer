# WriterAgent - AI Article Generation System

WriterAgent is an intelligent content generation system that uses A2A (Agent-to-Agent) Protocol to orchestrate SEO-optimized article creation, proofreading, and Word document export.

## System Architecture

The system consists of multiple specialized agents communicating through the A2A Protocol:

### Agents

1. **SEO Title Agent** (`seo_title_agent.py`)
   - Researches topics to identify SEO-optimized article titles
   - Analyzes search trends and keyword metrics
   - Generates titles with maximum SEO value
   - Communicates with WordPress Writer Agent via A2A Protocol

2. **WordPress Article Agent** (`wordpress_agent.py`)
   - Receives article generation requests via A2A messages
   - Generates SEO-optimized WordPress articles
   - Includes proper HTML structure (wp:paragraph, wp:heading, etc.)
   - Improves articles based on proofreader suggestions
   - Exports in multiple formats (JSON, XML, HTML)

3. **Proofreader Agent** (`proofreader_agent.py`)
   - Reviews articles and assigns SEO scores (1-10)
   - Provides specific improvement suggestions across 7 categories:
     - Title optimization
     - Content length
     - Keyword density
     - Heading structure
     - HTML structure and meta elements
     - Readability
     - Links and internal structure
   - Iteratively requests improvements until SEO score >= 8
   - Sends final HTML content to Publisher Agent for posting

4. **WordPress Publisher Agent** (`wordpress_publisher_agent.py`)
   - Receives HTML from Proofreader Agent
   - Publishes new posts to the configured WordPress site
   - Uses REST API with credentials (`WP_SITE_URL`, `WP_USER`, `WP_PASS`)
   - Returns post URL to orchestrator

5. **A2A Protocol Framework** (`a2a_protocol.py`)
   - Enables secure agent-to-agent communication
   - Message broker for routing between agents
   - Supports different message types (REQUEST, RESPONSE, ERROR)

4. **A2A Protocol Framework** (`a2a_protocol.py`)
   - Enables secure agent-to-agent communication
   - Message broker for routing between agents
   - Supports different message types (REQUEST, RESPONSE, ERROR)

5. **Orchestrator** (`orchestrator.py`)
   - Coordinates the complete A2A workflow
   - Registers agents with the message broker
   - Manages title generation, article creation, and proofreading
   - Automates Word document export

## Workflow

```
User Request
    ↓
[SEO Title Agent] → Generates optimized title
    ↓
[A2A Protocol Message]
    ↓
[WordPress Writer Agent] → Creates article
    ↓
[A2A Protocol Message]
    ↓
[Proofreader Agent] → Reviews & scores article
    ↓
[SEO Score >= 8?] 
    ├─ YES → Export to Word (.docx)
    └─ NO  → Request improvements (up to 3 iterations)
                ↓
            [WordPress Writer Agent] → Improves article
                ↓
            [Back to Proofreader Agent]
```

## Usage

### Basic Usage (Title Generation Only)

```bash
python seo_title_agent.py
```

Output: SEO-optimized article title

### Complete Workflow (Title → Article → Proofreading → Word Export)

```bash
python orchestrator.py
```

This will:
1. Generate an SEO-optimized title
2. Request article generation via A2A Protocol
3. Review article with Proofreader Agent
4. Request improvements if SEO score < 8 (up to 3 iterations)
5. Export final article to Word document when score >= 8

### SEO Scoring System

The Proofreader Agent evaluates articles across 7 criteria:

| Criterion | Max Points | Evaluation |
|-----------|-----------|-----------|
| Title Optimization | 15 | Length, power words, keyword inclusion |
| Content Length | 15 | Word count (optimal: 800-2500 words) |
| Keyword Density | 15 | Primary keyword (optimal: 1-3%) and variations |
| Heading Structure | 15 | H1, H2, H3 hierarchy and count |
| HTML Structure | 15 | WordPress blocks, paragraphs, lists |
| Readability | 10 | Sentence length and paragraph structure |
| Links | 10 | Internal/external links (optimal: 3-5) |
| **Total** | **100** | **Converted to 1-10 scale** |

## A2A Protocol

The A2A Protocol enables seamless communication between agents:

### Message Structure

```json
{
  "sender": "seo_title_agent",
  "receiver": "wordpress_writer_agent",
  "message_type": "request",
  "payload": {
    "title": "The Ultimate Guide to Artificial Intelligence in 2026",
    "topic": "Artificial Intelligence"
  }
}
```

### Message Types

- **REQUEST**: Agent requests action (e.g., generate/improve article)
- **RESPONSE**: Agent provides requested output
- **ERROR**: Communication or processing error occurred

## Output Formats

### WordPress Post - Primary Output
- SEO-optimized title and metadata
- Full article content in WordPress HTML block format
- Automatically created on configured site
- Post URL returned in workflow results

### Alternative Formats (JSON, XML, HTML)
- JSON: For programmatic import
- XML: WordPress WXR format for native import (archival)
- HTML: Standalone web files

## Features

### Intelligent Proofreading
- Automated SEO score calculation
- Specific, actionable improvement suggestions
- Iterative improvement loops
- Score history tracking

### SEO Optimization Engine
- Comprehensive keyword density analysis
- Optimal content length recommendations
- Heading structure validation
- Readability metrics
- Link strategy recommendations

### Seamless Agent Communication
- A2A Protocol for reliable messaging
- Message broker for routing
- Error handling and recovery
- Results caching

### WordPress Integration
- Native WordPress HTML block format
- Direct importer compatibility
- Metadata and post attributes
- SEO-ready structure

## Environment Variables

Optional environment variables for extended functionality:
- `OPENAI_API_KEY`: For enhanced AI features
- `SERPAPI_API_KEY`: For live SERP data and search trends
- `WP_SITE_URL`: Base URL of WordPress site (e.g. https://aitopchoices.com)
- `WP_USER`: WordPress username or application password user
- `WP_PASS`: WordPress password or application password

## Requirements

- Python 3.7+
- requests library
- python-docx library

Install dependencies:
```bash
pip install -r requirements.txt
```

## Architecture Benefits

1. **Modularity**: Each agent has a single responsibility
2. **Scalability**: New agents can be easily added
3. **Reliability**: Message broker ensures reliable communication
4. **Quality Assurance**: Proofreader ensures content quality
5. **Automation**: Iterative improvement loops reduce manual work
6. **Flexibility**: Agents can be combined in different workflows
7. **Extensibility**: Easy to add new metrics and handlers

## Example Workflow Output

When running the complete orchestration:
```
Title: The Ultimate Guide to Artificial Intelligence in 2026

[Iteration 1]
SEO Score: 10.0/10
Status: Ready for Publication ✓

Word File: article_The_Ultimate_Guide_to_Artificial_Intelligence_in_2_20260301_131138.docx
```

## Example API Usage

```python
from orchestrator import WriterAgentOrchestrator

orchestrator = WriterAgentOrchestrator()
result = orchestrator.orchestrate(topic="Artificial Intelligence")

print(f"Title: {result['title']}")
print(f"SEO Score: {result['seo_score']:.1f}/10")
print(f"Word File: {result['word_file']}")
```

## Files

- `seo_title_agent.py` - SEO Title generating agent
- `wordpress_agent.py` - WordPress article writing agent
- `proofreader_agent.py` - SEO review and scoring agent
- `a2a_protocol.py` - A2A Protocol framework
- `orchestrator.py` - Workflow orchestrator
- `requirements.txt` - Python dependencies

## License

See LICENSE file for details.
 
