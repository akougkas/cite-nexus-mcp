"""CiteNexus: scholarly evidence for research assistants."""

__version__ = "0.2.1"


def main() -> None:
    """Console entry point; importing the package has no side effects."""
    from .server import run

    run()


__all__ = ["__version__", "main"]
