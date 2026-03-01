#!/usr/bin/env python3
"""
ProofreaderAgent - SEO Scoring and Quality Assurance Module

The ProofreaderAgent is responsible for:
1. Analyzing articles across 7 SEO criteria
2. Assigning quality scores (1-10)
3. Providing actionable improvement suggestions
4. Requesting improvements via A2A Protocol
5. Iterating until quality threshold is met (>= 8.0)
6. Exporting final articles to Word format

SCORING CRITERIA
================

1. TITLE OPTIMIZATION (Max: 15 points)
   Evaluates:
   - Title length (optimal: 50-60 chars)
   - Power words (Ultimate, Complete, Guide, Best, etc.)
   - Main topic keyword inclusion
   
   Example Score Breakdown:
   ✓ Optimal length → +5
   ✓ Contains power words → +5
   ✓ Includes main keyword → +5
   Total: 15 points

2. CONTENT LENGTH (Max: 15 points)
   Evaluates:
   - Total word count
   - Optimal range: 800-2500 words
   
   Scoring:
   ✓ 800-2500 words → 15 points
   ✓ 500-800 words → 10 points
   ✗ < 500 words → 5 points
   ✓ > 2500 words → 12 points (consider splitting)

3. KEYWORD DENSITY (Max: 15 points)
   Evaluates:
   - Primary keyword occurrences
   - Keyword variations and related terms
   - Optimal density: 1-3%
   
   Scoring:
   ✓ 1-3% density → 8 points
   ✓ 3+ keyword variations → 7 points
   ✗ < 1% density → penalties
   ✗ > 5% density → penalties (keyword stuffing)

4. HEADING STRUCTURE (Max: 15 points)
   Evaluates:
   - H1 tag count (should be 1)
   - H2 subheadings (recommended: 3-5)
   - H3 subheadings (recommended: 2+)
   
   Scoring:
   ✓ Exactly 1 H1 → +5
   ✓ 3+ H2 headings → +5
   ✓ 2+ H3 headings → +5

5. HTML STRUCTURE (Max: 15 points)
   Evaluates:
   - WordPress block format (<!-- wp:... -->)
   - Paragraph count (recommended: 5+)
   - List elements (bullets/numbers)
   
   Scoring:
   ✓ Uses WordPress blocks → +5
   ✓ 5+ paragraphs → +5
   ✓ Contains lists → +5

6. READABILITY (Max: 10 points)
   Evaluates:
   - Average sentence length
   - Paragraph structure
   - Optimal sentence length: 15-20 words
   
   Scoring:
   ✓ 15-20 word avg sentences → +5
   ✓ Well-structured paragraphs → +5

7. LINKS (Max: 10 points)
   Evaluates:
   - Internal link count
   - External link count
   - Recommended: 3-5 total links
   
   Scoring:
   ✓ 3-5 links → +10
   ✓ 1-3 links → +5
   ✗ No links → +0

TOTAL: 100 points → Converted to 1-10 scale

IMPROVEMENT WORKFLOW
====================

Iteration 1:
├─ Analyze article
├─ Calculate score
├─ Generate suggestions
├─ Score >= 8.0? → YES: Export to Word
└─ Score < 8.0? → Request improvements

Iteration 2-3:
├─ Apply suggestions to article
├─ Re-analyze
├─ Calculate new score
├─ Track score progression
├─ Score >= 8.0? → YES: Export to Word
└─ Continue improving or max iterations reached

SUGGESTION TYPES
================

Content Improvements:
- "Content is 535 words; aim for 800-2500 words"
- "Add more keyword variations and related terms"
- "Incorporate related keywords: [list]"

Structure Improvements:
- "Missing H1 heading; add one main H1 per article"
- "Only 2 H2 heading(s); aim for at least 3-5"
- "Add more H3 subheadings under H2s"

Meta Improvements:
- "Title too short: 45 chars (optimal: 50-60)"
- "Title too long: 75 chars (optimal: 50-60)"
- "Add powerful words like 'Ultimate', 'Complete', 'Guide'"

Link Improvements:
- "Add more internal/external links (3-5 recommended)"

Readability Improvements:
- "Average sentence length: 25.3 words; optimal is 15-20"

API USAGE
=========

from proofreader_agent import ProofreaderAgent
from a2a_protocol import A2AMessageBroker

# Initialize
proofreader = ProofreaderAgent()
broker = A2AMessageBroker()
proofreader.set_message_broker(broker)

# Review and improve article
final_article, final_score = proofreader.review_and_improve(
    article_content=html_article,
    title="Article Title",
    topic="Main Topic",
    message_broker=broker,
    max_iterations=3
)

# Publish via WordPress Publisher Agent
if final_score >= 8.0:
    # send article to publisher using broker
    from a2a_protocol import A2AMessage, MessageType
    pub_msg = A2AMessage(
        sender="proofreader_agent",
        receiver="wordpress_publisher_agent",
        message_type=MessageType.REQUEST,
        payload={
            "request_type": "publish_article",
            "title": "Article Title",
            "content": final_article,
            "status": "publish",
            "seo_score": final_score
        }
    )
    resp = broker.send_message(pub_msg)
    if resp.message_type == MessageType.RESPONSE:
        print(f"Published at: {resp.payload.get('post_url')}")
    else:
        print("Publishing failed", resp.payload)


SCORE INTERPRETATION
====================

Score >= 8.0: ✓ Ready for Publication
             Article will be published to WordPress via Publisher Agent
             Meets all SEO best practices
             
Score 7.0-7.9: ⚠ Good Quality
              May need minor improvements
              Can be published with edits
              
Score 5.0-6.9: ✗ Needs Work
              Significant SEO issues
              Requires substantial revision
              
Score < 5.0:  ✗ Poor Quality
             Major issues across multiple criteria
             Complete rewrite may be needed

CONFIGURATION OPTIONS
=====================

WordPress Publishing:
- Triggered when score >= 8.0
- Sends HTML to Publisher Agent via broker
- Publisher creates live post on configured site

Iteration Limits:
- Default: 3 iterations max
- Configurable per workflow
- Prevents infinite loops

Score Threshold:
- Default: 8.0 (out of 10)
- Tunable based on quality requirements
- Each point = 10% improvement

COMMON ISSUES & SOLUTIONS
==========================

Content Too Short:
→ Add more sections with substantive content
→ Expand existing paragraphs
→ Add real-world examples

Low Keyword Density:
→ Add main topic naturally throughout content
→ Include keyword variations
→ Update section headers with keywords

Poor Structure:
→ Add proper H1/H2/H3 hierarchy
→ Break long paragraphs into shorter ones
→ Add bullet lists

Readability Issues:
→ Shorten sentences (15-20 word average)
→ Use simple language
→ Add transitional phrases

Missing Links:
→ Add 3-5 relevant internal/external links
→ Link to authoritative sources
→ Include related articles

"""

print(__doc__)
