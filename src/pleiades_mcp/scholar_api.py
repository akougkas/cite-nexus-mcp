"""
Simple SerpAPI wrapper for Google Scholar - the single source of truth.
"""
import os
from typing import Dict, List, Optional, Any
from serpapi import GoogleScholarSearch


class ScholarAPI:
    """Simple wrapper for SerpAPI Google Scholar searches."""

    def __init__(self):
        """Initialize with API key from environment."""
        self.api_key = os.getenv("SERP_API_KEY", "")
        if not self.api_key:
            raise ValueError("SERP_API_KEY environment variable not set")

    def find_paper(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Find a paper by title/query and return first result with cluster_id.

        Args:
            query: Search query (paper title or keywords)

        Returns:
            First result with cluster_id or None
        """
        search = GoogleScholarSearch({
            "q": query,
            "api_key": self.api_key,
            "num": 1
        })

        results = search.get_dict()
        organic_results = results.get("organic_results", [])

        if organic_results:
            paper = organic_results[0]
            # Extract cluster_id from the result
            if "inline_links" in paper:
                for key, link in paper["inline_links"].items():
                    if isinstance(link, dict):
                        if "cluster_id" in link:
                            paper["cluster_id"] = link["cluster_id"]
                            break
                        if "cites_id" in link:
                            paper["cluster_id"] = link["cites_id"]
                            break
                        if "serpapi_scholar_link" in link:
                            # Extract cluster ID from SerpAPI link
                            if "cluster" in link["serpapi_scholar_link"]:
                                import re
                                match = re.search(r'cluster=(\d+)', link["serpapi_scholar_link"])
                                if match:
                                    paper["cluster_id"] = match.group(1)
                                    break
            return paper
        return None

    def get_paper_by_id(self, cluster_id: str) -> Dict[str, Any]:
        """
        Direct lookup using cluster ID for complete metadata.

        Args:
            cluster_id: Google Scholar cluster ID

        Returns:
            Complete paper metadata
        """
        search = GoogleScholarSearch({
            "cluster": cluster_id,
            "api_key": self.api_key
        })

        return search.get_dict()

    def get_citations(self, cluster_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get papers citing this cluster_id.

        Args:
            cluster_id: Google Scholar cluster ID
            limit: Maximum number of citations to return

        Returns:
            List of citing papers
        """
        search = GoogleScholarSearch({
            "cites": cluster_id,
            "api_key": self.api_key,
            "num": min(limit, 20)
        })

        results = search.get_dict()
        return results.get("organic_results", [])