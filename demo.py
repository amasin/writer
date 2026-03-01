#!/usr/bin/env python3
"""
WriterAgent Demo - Complete Usage Example
Demonstrates the full article generation and proofreading workflow.
"""

import sys
from orchestrator import WriterAgentOrchestrator


def demo_complete_workflow():
    """
    Complete workflow demonstration: Title → Article → Proofreading → Word Export
    """
    print("=" * 80)
    print("WriterAgent - Complete Workflow Demo")
    print("=" * 80)
    print()
    
    # Initialize the orchestrator
    orchestrator = WriterAgentOrchestrator()
    
    # Run the complete orchestration
    print("Starting article generation workflow...\n")
    result = orchestrator.orchestrate(
        topic="Artificial Intelligence",
        output_title_only=False  # Show all output
    )
    
    # Show publish info
    if result.get('post_url'):
        print(f"\n✓ Published at: {result['post_url']}")
    else:
        err = result.get('post_url') or 'unknown error'
        print(f"\n✗ Publishing failed or score insufficient ({result['seo_score']:.1f}) - {err}")
    
    # Print results
    print("\n" + "=" * 80)
    print("WORKFLOW RESULTS")
    print("=" * 80)
    print(f"Title: {result['title']}")
    print(f"Topic: {result['topic']}")
    print(f"Final SEO Score: {result['seo_score']:.1f}/10")
    print(f"Status: {result['status'].upper()}")
    
    if result.get('word_file'):
        print(f"\n✓ Word Document Created: {result['word_file']}")
        print(f"  Ready for publication on any platform!")
    else:
        print(f"\n✗ Word Export: SEO score {result['seo_score']:.1f} < 8.0")
        print(f"  Document was not exported (requires score >= 8.0)")
    
    print("\n" + "=" * 80)
    
    return result


def demo_multi_topic():
    """
    Demonstration of generating articles for multiple topics
    """
    topics = [
        "Machine Learning",
        "Cloud Computing",
        "Cybersecurity"
    ]
    
    results = []
    
    for topic in topics:
        print(f"\nGenerating article for: {topic}")
        orchestrator = WriterAgentOrchestrator()
        result = orchestrator.orchestrate(
            topic=topic,
            output_title_only=False
        )
        results.append(result)
    
    print("\n" + "=" * 80)
    print("MULTI-TOPIC GENERATION SUMMARY")
    print("=" * 80)
    
    for result in results:
        status = "✓ Published" if result.get('word_file') else "✗ Pending"
        print(f"{result['topic']:20} | Score: {result['seo_score']:5.1f}/10 | {status}")
    
    return results


def main():
    """Main entry point for demo"""
    demo_type = "complete"  # Options: complete, multi
    
    if len(sys.argv) > 1:
        demo_type = sys.argv[1].lower()
    
    if demo_type == "multi":
        demo_multi_topic()
    else:
        demo_complete_workflow()


if __name__ == "__main__":
    main()
