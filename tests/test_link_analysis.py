"""Small contract checks for the public API request and route."""

import unittest

from app.main import app
from app.schemas import LinkAnalysisRequest


class LinkAnalysisContractTests(unittest.TestCase):
    def test_request_accepts_url_and_page_limit(self):
        request = LinkAnalysisRequest(url="https://example.com/", max_pages=2)
        self.assertEqual(request.max_pages, 2)
        self.assertEqual(str(request.url), "https://example.com/")

    def test_only_assignment_post_endpoint_is_registered(self):
        post_paths = [route.path for route in app.routes
                      if hasattr(route, "methods") and "POST" in route.methods]
        self.assertEqual(post_paths, ["/link-analysis"])


if __name__ == "__main__":
    unittest.main()

