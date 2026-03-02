import seo_brief


def test_build_brief_with_mocked_gsc():
    class DummyGSC:
        def get_queries_for_topic_seed(self, seeds):
            return []

    # Patch the get_gsc_client used by seo_brief
    orig = seo_brief.get_gsc_client
    seo_brief.get_gsc_client = lambda: DummyGSC()
    try:
        brief = seo_brief.build_brief("Artificial Intelligence")
        assert brief.topic == "Artificial Intelligence"
        assert isinstance(brief.secondary_keywords, list)
        assert isinstance(brief.suggested_title_patterns, list)
    finally:
        seo_brief.get_gsc_client = orig
