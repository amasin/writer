from wp_content_index import WPContentIndex


def test_extract_headings():
    html = "<h2>One</h2><h3>Two</h3><h2>Three</h2>"
    idx = WPContentIndex()
    headings = idx.extract_headings(html)
    assert "One" in headings and "Two" in headings and "Three" in headings


def test_load_or_build_mock():
    idx = WPContentIndex()
    posts = idx.load_or_build()
    assert isinstance(posts, list)
    assert len(posts) >= 1
    first = posts[0]
    assert "title" in first
