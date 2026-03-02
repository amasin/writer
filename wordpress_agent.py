#!/usr/bin/env python3
"""
WordPress Article Writer Agent.
Uses A2A protocol to receive titles and write SEO-optimized WordPress articles.
"""

import os
from typing import Dict, Any, Optional, List
from wp_index import load_or_build
from similarity import title_similarity, outline_similarity
from datetime import datetime
from a2a_protocol import A2AAgent, A2AMessage, MessageType, AgentType, A2AMessageBroker


class WordPressArticleAgent(A2AAgent):
    """Agent for writing SEO-optimized WordPress articles."""
    
    def __init__(self, agent_id: str = "wordpress_writer_agent"):
        """Initialize the WordPress Article Writer Agent."""
        super().__init__(agent_id, AgentType.WORDPRESS_WRITER_AGENT)
        self.articles: Dict[str, str] = {}
    
    def process_message(self, message: A2AMessage) -> A2AMessage:
        """
        Process incoming message.
        
        Args:
            message: The incoming A2A message
            
        Returns:
            Response message with article content
        """
        if message.message_type != MessageType.REQUEST:
            return A2AMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.ERROR,
                payload={"error": "Invalid message type"}
            )
        
        request_type = message.payload.get("request_type", "generate_article")
        title = message.payload.get("title", "")
        topic = message.payload.get("topic", "")
        brief = message.payload.get("brief")
        gsc_data = message.payload.get("gsc_data")
        # prefer passed index (for testability), otherwise build/load live index
        wp_index = message.payload.get("wp_index") or load_or_build()
        
        if not title:
            return A2AMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.ERROR,
                payload={"error": "Title not provided"}
            )
        
        if request_type == "improve_seo":
            # Handle improvement request from proofreader
            current_content = message.payload.get("content", "")
            seo_score = message.payload.get("seo_score", 0)
            suggestions = message.payload.get("suggestions", [])
            iteration = message.payload.get("iteration", 1)
            
            improved_content = self.improve_article_seo(
                current_content, title, topic, suggestions, iteration, gsc_data
            )
            
            self.articles[title] = improved_content
            
            return A2AMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.RESPONSE,
                payload={
                    "improved_content": improved_content,
                    "previous_score": seo_score,
                    "iteration": iteration + 1,
                    "format": "wordpress"
                }
            )
        else:
            # Original generate_article request
            # Duplicate detection: check title similarity against live posts
            try:
                posts = wp_index.index if hasattr(wp_index, "index") else list(wp_index)
            except Exception:
                posts = []

            for post in posts:
                if title and title_similarity(title, post.get("title", "")) >= 0.85:
                    return A2AMessage(
                        sender=self.agent_id,
                        receiver=message.sender,
                        message_type=MessageType.RESPONSE,
                        payload={
                            "duplicate": True,
                            "reason": "title_similar",
                            "existing_post": post,
                            "format": "wordpress"
                        }
                    )

            # Try to find an outline variation that is sufficiently different
            style_seed = int(message.payload.get("style_seed", 0))
            best_seed = style_seed
            best_score = 1.0
            for seed in range(0, 8):
                candidate_outline = self.generate_outline(topic, title, style_seed=seed)
                # compute worst-case similarity vs existing headings
                max_sim = 0.0
                for post in posts:
                    sim = outline_similarity(candidate_outline, post.get("headings", []))
                    if sim > max_sim:
                        max_sim = sim
                if max_sim < best_score:
                    best_score = max_sim
                    best_seed = seed

            # If even the best variation is too close to existing content, abort
            if best_score >= 0.75 and posts:
                return A2AMessage(
                    sender=self.agent_id,
                    receiver=message.sender,
                    message_type=MessageType.RESPONSE,
                    payload={
                        "duplicate": True,
                        "reason": "outline_similar",
                        "closest_similarity": best_score,
                        "format": "wordpress"
                    }
                )

            # Generate outline with the selected seed
            outline = self.generate_outline(topic, title, style_seed=best_seed)

            # Generate the article from outline
            article_content = self.write_article_from_outline(outline, topic, title, gsc_data)
            
            # Cache the article
            self.articles[title] = article_content
            
            return A2AMessage(
                sender=self.agent_id,
                receiver=message.sender,
                message_type=MessageType.RESPONSE,
                payload={
                    "title": title,
                    "content": article_content,
                    "outline": outline,
                    "seo_optimized": True,
                    "word_count": len(article_content.split()),
                    "format": "wordpress"
                }
            )
    
    def generate_article(self, title: str, topic: str = "Artificial Intelligence",
                         gsc_data: Dict[str, Any] = None) -> str:
        """
        Generate SEO-optimized WordPress article content using the outline-based system.
        
        This wrapper ensures external callers can still use generate_article even though the
        process_message logic now utilises the outline functions directly.
        
        Args:
            title: Article title
            topic: Main topic
            gsc_data: Optional insights from GSC to guide content
            
        Returns:
            WordPress-formatted article content
        """
        # default style seed 0
        outline = self.generate_outline(topic, title, style_seed=0)
        article = self.write_article_from_outline(outline, topic, title, gsc_data)
        return article
    
    def generate_outline(self, topic: str, title: str, style_seed: int = 0) -> list:
        """
        Generate article outline with varied structure based on style seed.
        Enables different outline variations for duplicate avoidance.
        
        Args:
            topic: Main article topic
            title: Article title
            style_seed: Variation seed (0-7) for different outline styles
            
        Returns:
            List of heading strings in hierarchical order
        """
        # Define multiple outline styles to vary article structure
        styles = [
            # Style 0: Traditional flow (What > Why > How > Examples > Future > FAQ)
            [
                f"What is {topic}?",
                f"Why {topic} Matters Today",
                f"Key Applications and Use Cases",
                f"Industry-Wide Impact of {topic}",
                f"Challenges and Opportunities",
                f"The Future of {topic}",
                "Frequently Asked Questions"
            ],
            # Style 1: Problem-Solution flow (Problem > Solutions > Implementation > Results > FAQ)
            [
                f"The {topic} Challenge",
                f"Understanding {topic} Solutions",
                f"Core Components and Features",
                f"Practical Implementation Strategies",
                f"Real-World Results and Case Studies",
                f"Best Practices for {topic}",
                "Frequently Asked Questions"
            ],
            # Style 2: Comprehensive guide (Basics > Advanced > Tools > Trends > Tips > FAQ)
            [
                f"{topic} Fundamentals",
                f"Getting Started with {topic}",
                f"Advanced {topic} Concepts",
                f"Popular Tools and Technologies",
                f"Current Trends in {topic}",
                f"Expert Tips and Best Practices",
                "Frequently Asked Questions"
            ],
            # Style 3: Industry-focused (Overview > Sectors > Benefits > Implementation > Future > FAQ)
            [
                f"Overview of {topic}",
                f"{topic} Across Different Industries",
                f"Key Benefits and Advantages",
                f"Implementation Considerations",
                f"ROI and Business Impact",
                f"Future Outlook for {topic}",
                "Frequently Asked Questions"
            ],
            # Style 4: Comparison-heavy (Definition > Comparisons > Evaluation > Recommendations > FAQ)
            [
                f"What Exactly is {topic}?",
                f"{topic} vs. Related Technologies",
                f"Evaluating {topic} Solutions",
                f"Comparing Popular {topic} Platforms",
                f"How to Choose the Right {topic} Solution",
                f"Recommendations and Conclusion",
                "Frequently Asked Questions"
            ],
            # Style 5: Timeline-based (History > Evolution > Current State > Future > Conclusion > FAQ)
            [
                f"The Evolution of {topic}",
                f"Historical Development and Milestones",
                f"Modern Applications of {topic}",
                f"The Current {topic} Landscape",
                f"Emerging Trends and Innovations",
                f"The Future of {topic}",
                "Frequently Asked Questions"
            ],
            # Style 6: Detailed guide (Introduction > Deep Dive > Variations > Strategies > Metrics > FAQ)
            [
                f"Introduction to {topic}",
                f"Deep Dive: Understanding {topic} Core",
                f"Types and Variations of {topic}",
                f"Strategic Approaches to {topic}",
                f"Measuring {topic} Success",
                f"Optimization and Best Practices",
                "Frequently Asked Questions"
            ],
            # Style 7: Practical focus (Concepts > Tools > Workflows > Pitfalls > Mastery > FAQ)
            [
                f"{topic} Concepts Explained",
                f"Tools and Platforms for {topic}",
                f"Common Workflows and Processes",
                f"Avoiding Common {topic} Pitfalls",
                f"Advanced Techniques and Mastery",
                f"Integration and Scaling {topic}",
                "Frequently Asked Questions"
            ]
        ]
        
        # Select outline based on style seed
        selected_outline = styles[style_seed % len(styles)]
        return selected_outline
    
    def write_article_from_outline(self, outline: list, topic: str, title: str,
                                   gsc_data: Dict[str, Any] = None) -> str:
        """
        Write article content structured according to provided outline.
        
        Args:
            outline: List of heading strings defining article structure
            topic: Main topic
            title: Article title
            gsc_data: Optional GSC insights
            
        Returns:
            Complete WordPress-formatted article
        """
        content = []
        
        # Opening paragraph
        content.append(f"""<!-- wp:paragraph -->
<p><strong>{title}</strong> is becoming increasingly important in today's digital landscape. As organizations worldwide embrace innovation, understanding {topic.lower()} has never been more critical. This comprehensive guide explores everything you need to know about {topic.lower()}, from foundational concepts to advanced applications.</p>
<!-- /wp:paragraph -->""")
        
        # Table of contents
        toc_items = "\n".join(f"<li>{heading}</li>" for heading in outline if heading != "Frequently Asked Questions")
        content.append(f"""<!-- wp:heading {{"level":2}} -->
<h2>Table of Contents</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul>
{toc_items}
<li>Frequently Asked Questions</li>
</ul>
<!-- /wp:list -->""")
        
        # Main sections based on outline
        for heading in outline:
            if heading == "Frequently Asked Questions":
                # FAQ section
                content.append(self._generate_faq(topic))
            else:
                # Generate content for each heading
                section_content = self._generate_section_from_heading(heading, topic)
                content.append(section_content)
        
        # Conclusion
        content.append(f"""<!-- wp:heading {{"level":2}} -->
<h2>Conclusion</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{topic} is no longer a future technology—it's reshaping our present. Organizations that understand and embrace {topic.lower()} will thrive in an increasingly competitive landscape. Whether you're just beginning your {topic.lower()} journey or looking to deepen your expertise, the time to act is now. Start exploring practical solutions that align with your goals and position your organization for long-term success.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Ready to harness the power of {topic.lower()}? Explore solutions that drive real business value and transform your operations today.</strong></p>
<!-- /wp:paragraph -->""")
        
        article = "\n\n".join(content)
        
        if gsc_data:
            site_perf = gsc_data.get("site_performance", {})
            if site_perf.get("ctr", 1) < 0.02:
                article += "\n<!-- wp:paragraph --><p>Note: previous content had low click-through rate; consider improving meta description.</p><!-- /wp:paragraph -->"
        
        return article
    
    def _generate_section_from_heading(self, heading: str, topic: str) -> str:
        """
        Generate content section for a given heading.
        
        Args:
            heading: The heading text
            topic: Article topic for context
            
        Returns:
            WordPress-formatted section
        """
        # Map common heading patterns to paragraph content
        content_map = {
            "What": f"""<!-- wp:heading {{"level":2}} -->
<h2>{heading}</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{topic} refers to a comprehensive set of principles and practices designed to solve modern challenges. Understanding the fundamental concepts is essential for effective implementation. This section breaks down core definitions and key terminology.</p>
<!-- /wp:paragraph -->""",
            
            "Why": f"""<!-- wp:heading {{"level":2}} -->
<h2>{heading}</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>The importance of {topic.lower()} cannot be overstated in today's competitive environment. Organizations that leverage {topic.lower()} effectively gain significant advantages in efficiency, decision-making, and innovation. Understanding the value proposition is critical for stakeholder buy-in.</p>
<!-- /wp:paragraph -->""",
            
            "How": f"""<!-- wp:heading {{"level":2}} -->
<h2>{heading}</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Implementation of {topic.lower()} follows a structured approach. Start with clear objectives and realistic timelines. Assess current capabilities and identify skill gaps. Build in phases, starting with pilot projects before full-scale deployment. Monitor progress and adjust strategies based on results.</p>
<!-- /wp:paragraph -->""",
            
            "Key": f"""<!-- wp:heading {{"level":2}} -->
<h2>{heading}</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Several key applications demonstrate the versatility of {topic.lower()}. From optimizing operations to enhancing customer experiences, the practical benefits are substantial. Real-world implementations across industries validate the approach and provide valuable lessons for others.</p>
<!-- /wp:paragraph -->""",
            
            "Industry": f"""<!-- wp:heading {{"level":2}} -->
<h2>{heading}</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{topic} is transforming multiple industries simultaneously. Healthcare organizations improve patient outcomes. Financial institutions enhance risk management. Manufacturing increases productivity. Retail companies personalize customer journeys. The cross-industry impact demonstrates universal applicability.</p>
<!-- /wp:paragraph -->""",
            
            "Challenge": f"""<!-- wp:heading {{"level":2}} -->
<h2>{heading}</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{topic} implementation faces real obstacles that organizations must navigate. Technical complexity requires skilled professionals. Legacy system integration can be time-consuming. Change management often faces organizational resistance. Understanding these challenges enables better planning and risk mitigation.</p>
<!-- /wp:paragraph -->""",
            
            "Future": f"""<!-- wp:heading {{"level":2}} -->
<h2>{heading}</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Looking ahead, {topic.lower()} will continue evolving at an accelerating pace. Emerging technologies promise enhanced capabilities and broader applications. New standards and best practices will emerge. Organizations that stay informed and adapt will lead their industries. The next era of {topic.lower()} innovation is just beginning.</p>
<!-- /wp:paragraph -->""",
            
            "Best": f"""<!-- wp:heading {{"level":2}} -->
<h2>{heading}</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Success with {topic.lower()} requires adherence to proven best practices. Start with clear strategy alignment. Invest in employee training and development. Implement robust governance and oversight. Foster continuous learning and improvement. Share knowledge across teams and departments.</p>
<!-- /wp:paragraph -->""",
            
            "Tool": f"""<!-- wp:heading {{"level":2}} -->
<h2>{heading}</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Modern {topic.lower()} relies on sophisticated tools and platforms. Leading solutions offer robust feature sets, scalability, and reliability. Evaluation should consider integration capabilities, ease of use, and long-term support. Community adoption and vendor stability matter for long-term success.</p>
<!-- /wp:paragraph -->""",
        }
        
        # Find matching pattern
        for pattern, template in content_map.items():
            if pattern.lower() in heading.lower():
                return template
        
        # Default section if no pattern matches
        return f"""<!-- wp:heading {{"level":2}} -->
<h2>{heading}</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>This section explores important aspects of {topic.lower()} relevant to the discussion. Understanding these concepts helps organizations make informed decisions and develop effective strategies. Practical implementation requires careful consideration of organizational context and goals.</p>
<!-- /wp:paragraph -->"""
    
    def improve_article_seo(self, current_content: str, title: str, topic: str,
                            suggestions: list, iteration: int,
                            gsc_data: Dict[str, Any] = None) -> str:
        """
        Improve article based on SEO suggestions.
        
        Args:
            current_content: Current article content
            title: Article title
            topic: Main topic
            suggestions: List of SEO improvement suggestions
            iteration: Current iteration number
            gsc_data: Optional GSC insights to inform changes
            
        Returns:
            Improved article content
        """
        # Start with current content and enhance it
        improved_content = current_content

        # if gsc_data suggests low_ctr, optionally adjust intro
        if gsc_data:
            site_perf = gsc_data.get("site_performance", {})
            if site_perf.get("ctr", 1) < 0.02:
                improved_content += "\n<!-- wp:paragraph --><p><em>CTA: improve click-through by revising headline or meta description.</em></p><!-- /wp:paragraph -->"
        
        # Apply specific improvements based on suggestions
        for suggestion in suggestions[:3]:  # Apply top 3 suggestions
            improved_content = self._apply_suggestion(improved_content, suggestion, title, topic)
        
        return improved_content
        # Start with current content and enhance it
        improved_content = current_content
        
        # Apply specific improvements based on suggestions
        for suggestion in suggestions[:3]:  # Apply top 3 suggestions
            improved_content = self._apply_suggestion(improved_content, suggestion, title, topic)
        
        return improved_content
    
    def _apply_suggestion(self, content: str, suggestion: str, title: str, topic: str) -> str:
        """Apply a specific SEO suggestion to the article."""
        import re
        
        # Keyword density improvements
        if "keyword density" in suggestion.lower():
            # Add more instances of the main topic
            # Find a good place to add the keyword naturally
            topic_lower = topic.lower()
            
            # Look for section headers and add the topic near them
            sections = content.split("<!-- /wp:paragraph -->")
            for i in range(len(sections)):
                if f"<h2" in sections[i] and topic_lower not in sections[i].lower():
                    # Add the topic term after this section header
                    match = re.search(r"(</h2>\s*<!-- wp:paragraph -->)", sections[i])
                    if match:
                        sections[i] = sections[i].replace(
                            match.group(1),
                            match.group(1) + f"\n<p>{topic} is essential for this section.</p>\n<!-- /wp:paragraph -->"
                        )
                        break
            content = "<!-- /wp:paragraph -->".join(sections)
        
        # Length improvement
        if "words" in suggestion.lower() and "aim for" in suggestion.lower():
            # Add additional paragraphs with content
            additional_section = f"""<!-- wp:heading {{"level":2}} -->
<h2>Additional Insights on {topic}</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{topic} continues to evolve with new developments and applications emerging regularly. Understanding the nuances of {topic.lower()} implementation helps organizations make informed decisions. As enterprises increasingly adopt {topic.lower()} solutions, the importance of staying updated with the latest trends cannot be overstated. Implementation strategies should be tailored to specific organizational needs and capabilities.</p>
<!-- /wp:paragraph -->"""
            
            # Add before FAQ section
            if "Frequently Asked Questions" in content:
                content = content.replace(
                    "<!-- wp:heading",
                    additional_section + "\n\n<!-- wp:heading",
                    1
                )
            else:
                content = content + "\n\n" + additional_section
        
        # Heading structure improvement
        if "H2" in suggestion or "H3" in suggestion or "heading" in suggestion.lower():
            # Enhance heading structure
            if "Key Applications" in content and "<h3" not in content:
                # Add H3 subheadings under key sections
                content = content.replace(
                    "Key Applications and Use Cases</h2>",
                    'Key Applications and Use Cases</h2>\n\n<!-- wp:heading {"level":3} -->\n<h3>Practical Use Cases</h3>\n<!-- /wp:heading -->'
                )
        
        # Link improvement
        if "links" in suggestion.lower():
            # Add or enhance links
            if "href=" not in content:
                # Add some internal link examples
                content = content.replace(
                    "machine learning",
                    '<a href="#">machine learning</a>',
                    1
                )
        
        return content
    
    def _generate_wordpress_content(self, title: str, topic: str) -> str:
        """Generate WordPress article with full structure and SEO optimization."""
        
        # WordPress article structure with SEO optimizations
        content = []
        
        # Opening paragraph - high keyword density
        content.append(self._generate_opening(title, topic))
        
        # Table of contents (SEO best practice)
        content.append(self._generate_toc())
        
        # Main body sections (keyword optimized)
        content.append(self._generate_sections(title, topic))
        
        # FAQ section (improves SERP features)
        content.append(self._generate_faq(topic))
        
        # Conclusion with call-to-action
        content.append(self._generate_conclusion(topic))
        
        return "\n\n".join(content)
    
    def _generate_opening(self, title: str, topic: str) -> str:
        """Generate compelling opening paragraph with SEO keywords."""
        opening = f"""<!-- wp:paragraph -->
<p><strong>{title}</strong> is becoming increasingly important in today's digital landscape. As organizations worldwide embrace innovation, understanding {topic.lower()} has never been more critical. This comprehensive guide explores everything you need to know about {topic.lower()}, from foundational concepts to advanced applications.</p>
<!-- /wp:paragraph -->"""
        return opening
    
    def _generate_toc(self) -> str:
        """Generate table of contents."""
        toc = """<!-- wp:heading {"level":2} -->
<h2>Table of Contents</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul><li>What is Artificial Intelligence?</li><li>Key Applications and Use Cases</li><li>Industry-Wide Impact</li><li>Challenges and Opportunities</li><li>The Future of AI</li><li>Best Practices and Recommendations</li><li>Frequently Asked Questions</li></ul>
<!-- /wp:list -->"""
        return toc
    
    def _generate_sections(self, title: str, topic: str) -> str:
        """Generate main body sections with SEO optimization."""
        sections = []
        
        # Section 1
        sections.append("""<!-- wp:heading {"level":2} -->
<h2>What is Artificial Intelligence?</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Artificial Intelligence (AI) refers to computer systems designed to perform tasks that typically require human intelligence. These capabilities include visual perception, speech recognition, decision-making, and language translation. AI has evolved from theoretical research to practical applications across virtually every industry.</p>
<!-- /wp:paragraph -->""")
        
        # Section 2
        sections.append("""<!-- wp:heading {"level":2} -->
<h2>Key Applications and Use Cases</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>The applications of artificial intelligence are vast and growing. Machine learning powers recommendation systems, predictive analytics, and autonomous vehicles. Natural language processing enables chatbots and virtual assistants. Computer vision transforms healthcare, manufacturing, and security. These real-world implementations demonstrate the transformative potential of AI technology.</p>
<!-- /wp:paragraph -->""")
        
        # Section 3
        sections.append("""<!-- wp:heading {"level":2} -->
<h2>Industry-Wide Impact of AI</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Artificial Intelligence is reshaping industries from healthcare to finance. In healthcare, AI accelerates drug discovery and improves diagnostic accuracy. Financial institutions leverage AI for fraud detection and risk assessment. Retail companies use AI to personalize customer experiences. Manufacturing benefits from predictive maintenance and quality control. The strategic implementation of AI provides competitive advantages across sectors.</p>
<!-- /wp:paragraph -->""")
        
        # Section 4
        sections.append("""<!-- wp:heading {"level":2} -->
<h2>Challenges and Opportunities</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>While artificial intelligence offers tremendous opportunities, it also presents challenges. Data privacy and security remain critical concerns. Algorithmic bias requires careful attention during development. Regulatory compliance evolves rapidly across jurisdictions. However, organizations that address these challenges position themselves to capitalize on AI's transformative potential. Responsible AI development is essential for sustainable innovation.</p>
<!-- /wp:paragraph -->""")
        
        # Section 5
        sections.append("""<!-- wp:heading {"level":2} -->
<h2>The Future of Artificial Intelligence</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Looking ahead, artificial intelligence will continue advancing at an accelerating pace. Multimodal AI combining text, image, and audio processing is emerging. Autonomous agents will handle increasingly complex tasks. Human-AI collaboration will redefine workplace dynamics. Understanding these trends positions professionals and organizations for future success. The AI revolution is just beginning, and the opportunities ahead are extraordinary.</p>
<!-- /wp:paragraph -->""")
        
        return "\n\n".join(sections)
    
    def _generate_faq(self, topic: str) -> str:
        """Generate FAQ section for SERP features."""
        faq = """<!-- wp:heading {"level":2} -->
<h2>Frequently Asked Questions</h2>
<!-- /wp:heading -->

<!-- wp:heading {"level":3} -->
<h3>How is AI different from Machine Learning?</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>AI is the broader field of creating intelligent machines, while machine learning is a subset focusing on systems that learn from data without explicit programming. All machine learning is AI, but not all AI relies on machine learning.</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3>What are the main advantages of implementing AI?</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>AI implementation offers increased efficiency, improved decision-making, cost reduction, enhanced customer experiences, and competitive advantage. Organizations can automate routine tasks, uncover insights from data, and scale operations effectively.</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3>Which industries benefit most from AI?</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Healthcare, finance, retail, manufacturing, and telecommunications are among the industries gaining significant benefits. However, AI applications are emerging across all sectors, from agriculture to entertainment.</p>
<!-- /wp:paragraph -->"""
        
        return faq
    
    def _generate_conclusion(self, topic: str) -> str:
        """Generate conclusion with call-to-action."""
        conclusion = f"""<!-- wp:heading {"level":2} -->
<h2>Conclusion</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Artificial Intelligence is no longer a future technology—it's reshaping our present. Organizations that understand and embrace {topic.lower()} will thrive in an increasingly competitive landscape. Whether you're just beginning your AI journey or looking to deepen your expertise, the time to act is now. Start exploring practical AI solutions that align with your goals and position your organization for long-term success.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Ready to harness the power of artificial intelligence? Explore AI solutions that drive real business value and transform your operations today.</strong></p>
<!-- /wp:paragraph -->"""
        
        return conclusion
    
    def extract_headings(self, content: str) -> list:
        """
        Extract all headings (H2, H3) from WordPress article content.
        Used for duplicate outline detection.
        
        Args:
            content: WordPress HTML content
            
        Returns:
            List of heading text values
        """
        import re
        headings = []
        
        # Extract H2 headings
        h2_matches = re.findall(r'<h2[^>]*>([^<]+)</h2>', content)
        headings.extend(h2_matches)
        
        # Extract H3 headings
        h3_matches = re.findall(r'<h3[^>]*>([^<]+)</h3>', content)
        headings.extend(h3_matches)
        
        return headings
    
    def export_wordpress(self, title: str, output_format: str = "json") -> Optional[str]:
        """
        Export article in WordPress-compatible format.
        
        Args:
            title: Article title
            output_format: Format for export (json, xml, html)
            
        Returns:
            Formatted content for WordPress import
        """
        article = self.articles.get(title)
        if not article:
            return None
        
        if output_format == "json":
            return self._export_as_json(title, article)
        elif output_format == "xml":
            return self._export_as_xml(title, article)
        else:
            return article
    
    def _export_as_json(self, title: str, content: str) -> str:
        """Export as JSON format."""
        import json
        data = {
            "title": title,
            "content": content,
            "post_type": "post",
            "status": "draft",
            "format": "standard",
            "created_at": datetime.now().isoformat(),
            "meta": {
                "seo_optimized": True,
                "word_count": len(content.split())
            }
        }
        return json.dumps(data, indent=2)
    
    def _export_as_xml(self, title: str, content: str) -> str:
        """Export as XML format for WordPress import."""
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
  <title>WordPress Article Export</title>
  <item>
    <title>{self._escape_xml(title)}</title>
    <content:encoded><![CDATA[{content}]]></content:encoded>
    <wp:post_type>post</wp:post_type>
    <wp:post_name>{self._slugify(title)}</wp:post_name>
    <wp:post_date>{datetime.now().isoformat()}</wp:post_date>
  </item>
</channel>
</rss>"""
        return xml
    
    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape XML special characters."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    @staticmethod
    def _slugify(text: str) -> str:
        """Convert title to URL slug."""
        return text.lower().replace(" ", "-").replace(":", "").replace("?", "")
