"""Built-in scholarly sources; all adapters use the shared HTTP policy."""

from ..config import Settings
from ..http import HTTP
from .academic import Arxiv, EuropePMC
from .base import Provider
from .commercial import Scopus, SerpAPI, WebOfScience
from .graphs import OpenAlex, SemanticScholar
from .open_metadata import Crossref, DataCite


def registry(http: HTTP, settings: Settings) -> dict[str, Provider]:
    classes = (
        Crossref,
        DataCite,
        EuropePMC,
        Arxiv,
        SemanticScholar,
        OpenAlex,
        SerpAPI,
        Scopus,
        WebOfScience,
    )
    return {provider.id: provider(http, settings) for provider in classes}
