#!/usr/bin/env python3
"""
WriterAgent Orchestrator - Main Entry Point.
Orchestrates the SEO Title Agent, WordPress Writer Agent, and Proofreader Agent using A2A Protocol.
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# load environment variables from .env file automatically
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / '.env', override=True)
except ImportError:
    pass

from a2a_protocol import A2AMessageBroker, A2AMessage, MessageType
from seo_title_agent import SEOTitleAgent
from wordpress_agent import WordPressArticleAgent
from proofreader_agent import ProofreaderAgent
from wordpress_publisher_agent import WordPressPublisherAgent
from gsc_performance_agent import GSCPerformanceAgent
from wp_content_index import WPContentIndex


class WriterAgentOrchestrator:
    """Orchestrates the WriterAgent system with A2A Protocol."""
    
    def __init__(self):
        """Initialize the orchestrator."""
        self.broker = A2AMessageBroker()
        self.seo_agent = SEOTitleAgent(agent_id="seo_title_agent")
        self.wordpress_agent = WordPressArticleAgent(agent_id="wordpress_writer_agent")
        self.proofreader_agent = ProofreaderAgent(agent_id="proofreader_agent")
        self.publisher_agent = WordPressPublisherAgent(agent_id="wordpress_publisher_agent")
        self.gsc_agent = GSCPerformanceAgent(agent_id="gsc_performance_agent")
        
        # Register agents with broker
        self.broker.register_agent(self.seo_agent)
        self.broker.register_agent(self.wordpress_agent)
        self.broker.register_agent(self.proofreader_agent)
        self.broker.register_agent(self.publisher_agent)
        self.broker.register_agent(self.gsc_agent)
        
        # Set broker for agents
        self.seo_agent.set_message_broker(self.broker)
        self.proofreader_agent.set_message_broker(self.broker)
        self.publisher_agent.set_message_broker(self.broker)
        self.gsc_agent.set_message_broker(self.broker)
    
    def orchestrate(self, topic: str, output_title_only: bool = True) -> dict:
        """
        Orchestrate the complete workflow: title generation -> article creation -> proofreading -> Word export.
        
        Args:
            topic: The topic to write about
            output_title_only: If True, only output the title to stdout
            
        Returns:
            Dictionary with title, article content, and SEO score
        """
        print(f"[Orchestrator] Starting comprehensive workflow for topic: {topic}", file=sys.stderr)
        
        # Step 0: Load WordPress content index
        print("[Orchestrator] Step 0: Loading WordPress content index...", file=sys.stderr)
        wp_index = WPContentIndex()
        wp_posts = wp_index.load_or_build()
        print(f"[Orchestrator] Loaded {len(wp_posts)} posts from WordPress", file=sys.stderr)
        
        # Step 1: Retrieve GSC performance insights
        print("[Orchestrator] Step 1: Fetching GSC performance data...", file=sys.stderr)
        gsc_data = {}
        try:
            msg = A2AMessage(
                sender="orchestrator",
                receiver="gsc_performance_agent",
                message_type=MessageType.REQUEST,
                payload={"request_type": "analyze_site"}
            )
            resp = self.broker.send_message(msg)
            if resp and resp.message_type == MessageType.RESPONSE:
                gsc_data = resp.payload.get("gsc_data", {})
                print(f"[Orchestrator] GSC data retrieved", file=sys.stderr)
        except Exception as e:
            print(f"[Orchestrator] Failed to get GSC data: {e}", file=sys.stderr)

        # Step 2: Generate and filter SEO-optimized title
        print("[Orchestrator] Step 2: Generating title candidates...", file=sys.stderr)
        seo_agent = self.seo_agent
        
        best_title = None
        max_attempts = 3
        for attempt in range(max_attempts):
            candidates = seo_agent.generate_title_candidates(topic, n=20)
            
            # Filter out duplicates
            valid_candidates = []
            for candidate in candidates:
                dup_check = wp_index.find_duplicate_title(candidate, threshold=0.85)
                if not dup_check["is_duplicate"]:
                    valid_candidates.append(candidate)
                else:
                    matches = dup_check.get("matches", [])
                    print(f"[Orchestrator] Title rejected (duplicate): '{candidate}'", file=sys.stderr)
                    for match in matches[:1]:
                        print(f"  - Similar to: {match['title']} ({match['similarity']})", file=sys.stderr)
            
            if valid_candidates:
                # Score the valid candidates
                scored = []
                for title in valid_candidates:
                    score = seo_agent._calculate_seo_score(title)
                    scored.append({"title": title, "score": score})
                
                scored = sorted(scored, key=lambda x: x["score"], reverse=True)
                best_title = scored[0]["title"]
                print(f"[Orchestrator] Selected title: {best_title} (attempt {attempt+1})", file=sys.stderr)
                break
            elif attempt < max_attempts - 1:
                print(f"[Orchestrator] All candidates were duplicates, regenerating... (attempt {attempt+1}/{max_attempts})", file=sys.stderr)
        
        if not best_title:
            best_title = f"Comprehensive Guide to {topic} in 2026"
            print(f"[Orchestrator] Using fallback title: {best_title}", file=sys.stderr)
        
        # Output title to stdout (primary output)
        if output_title_only:
            print(best_title)
        
        # Step 3: Request article generation via A2A Protocol
        print("[Orchestrator] Step 3: Requesting article generation via A2A Protocol...", file=sys.stderr)
        
        # Create A2A message
        message = A2AMessage(
            sender="seo_title_agent",
            receiver="wordpress_writer_agent",
            message_type=MessageType.REQUEST,
            payload={
                "title": best_title,
                "topic": topic,
                "request_type": "generate_article",
                "seo_optimized": True,
                "gsc_data": gsc_data,
                "wp_index": wp_posts
            }
        )
        
        # Send through broker
        print("[Orchestrator] Step 4: Sending message through A2A broker...", file=sys.stderr)
        response = self.broker.send_message(message)
        
        # Extract article content and outline
        article_content = None
        outline = []
        if response.message_type == MessageType.RESPONSE:
            print("[Orchestrator] Step 5: Received article from WordPress Agent", file=sys.stderr)
            article_content = response.payload.get("content", "")
            outline = response.payload.get("outline", [])
        
        if not article_content:
            return {
                "title": best_title,
                "topic": topic,
                "article_content": None,
                "seo_score": 0,
                "word_file": None,
                "timestamp": datetime.now().isoformat(),
                "status": "error"
            }
        
        # Step 5b: Filter outline against WordPress for duplicates
        print("[Orchestrator] Step 5b: Filtering outline against WordPress...", file=sys.stderr)
        max_outline_attempts = 3
        for outline_attempt in range(max_outline_attempts):
            dup_outline_check = wp_index.find_duplicate_outline(outline, threshold=0.7)
            if not dup_outline_check["is_duplicate"]:
                print(f"[Orchestrator] Outline approved (attempt {outline_attempt+1})", file=sys.stderr)
                break
            else:
                matches = dup_outline_check.get("matches", [])
                matched_count = 0
                if matches:
                    matched_count = matches[0].get("shared_sections", 0)
                print(f"[Orchestrator] Outline rejected (duplicate): {matched_count}/{len(outline)} headings match existing content", file=sys.stderr)
                for match in matches[:1]:
                    print(f"  - Article: {match['title']} ({match['similarity']})", file=sys.stderr)
                
                if outline_attempt < max_outline_attempts - 1:
                    # Regenerate with different style_seed
                    style_seed = outline_attempt + 1
                    print(f"[Orchestrator] Regenerating outline with style_seed={style_seed}... (attempt {outline_attempt+2}/{max_outline_attempts})", file=sys.stderr)
                    
                    regen_msg = A2AMessage(
                        sender="orchestrator",
                        receiver="wordpress_writer_agent",
                        message_type=MessageType.REQUEST,
                        payload={
                            "title": best_title,
                            "topic": topic,
                            "request_type": "generate_article",
                            "seo_optimized": True,
                            "gsc_data": gsc_data,
                            "wp_index": wp_posts,
                            "style_seed": style_seed
                        }
                    )
                    
                    regen_response = self.broker.send_message(regen_msg)
                    if regen_response.message_type == MessageType.RESPONSE:
                        article_content = regen_response.payload.get("content", article_content)
                        outline = regen_response.payload.get("outline", outline)
                        print(f"[Orchestrator] Regenerated article with new outline", file=sys.stderr)
                    else:
                        print(f"[Orchestrator] Regeneration failed, keeping previous outline", file=sys.stderr)
        
        
        # Step 6: Proofread and improve article
        print("[Orchestrator] Step 6: Starting proofreader review process...", file=sys.stderr)
        
        final_article, final_seo_score = self.proofreader_agent.review_and_improve(
            article_content=article_content,
            title=best_title,
            topic=topic,
            message_broker=self.broker,
            max_iterations=3,
            gsc_data=gsc_data,
            wp_index_pages=wp_posts,
            outline=outline
        )
        
        # Step 7: Publish article if SEO score >= 8
        post_url = None
        if final_seo_score >= 8.0:
            print("[Orchestrator] Step 8: Sending article to publisher agent...", file=sys.stderr)
            pub_msg = A2AMessage(
                sender="proofreader_agent",
                receiver="wordpress_publisher_agent",
                message_type=MessageType.REQUEST,
                payload={
                    "request_type": "publish_article",
                    "title": best_title,
                    "content": final_article,
                    "status": "publish",
                    "seo_score": final_seo_score
                }
            )
            resp = self.broker.send_message(pub_msg)
            if resp and resp.message_type == MessageType.RESPONSE:
                post_url = resp.payload.get("post_url")
                print(f"[Orchestrator] Article published at: {post_url}", file=sys.stderr)
            else:
                err = resp.payload.get("error") if resp else "no response"
                print(f"[Orchestrator] Publishing failed: {err}", file=sys.stderr)
        
        result = {
            "title": best_title,
            "topic": topic,
            "article_content": final_article,
            "seo_score": final_seo_score,
            "post_url": post_url,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
        return result
    
    def save_article(self, title: str, article_content: str, format: str = "json") -> str:
        """
        Save article to file.
        
        Args:
            title: Article title
            article_content: Article content
            format: Output format (json, html, xml)
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            filename = f"article_{timestamp}.json"
            data = {
                "title": title,
                "content": article_content,
                "created_at": datetime.now().isoformat(),
                "format": "wordpress"
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        elif format == "html":
            filename = f"article_{timestamp}.html"
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <article>
        <h1>{title}</h1>
        <div class="content">
            {article_content}
        </div>
    </article>
</body>
</html>"""
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        elif format == "xml":
            filename = f"article_{timestamp}.xml"
            xml_content = self.wordpress_agent.export_wordpress(title, output_format="xml")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(xml_content)
        
        return filename


def main():
    """Main entry point for WriterAgent system."""
    orchestrator = WriterAgentOrchestrator()
    
    # Run the complete orchestration with proofreading and Word export
    result = orchestrator.orchestrate(
        topic="Artificial Intelligence",
        output_title_only=True
    )
    
    # Print final status
    print(f"[Orchestrator] Workflow completed!", file=sys.stderr)
    print(f"[Orchestrator] Final SEO Score: {result.get('seo_score', 0):.1f}/10", file=sys.stderr)
    
    if result.get("post_url"):
        print(f"[Orchestrator] Article published at: {result['post_url']}", file=sys.stderr)
    else:
        print(f"[Orchestrator] SEO score {result.get('seo_score', 0):.1f} < 8.0 or publish failed", file=sys.stderr)


if __name__ == "__main__":
    main()
