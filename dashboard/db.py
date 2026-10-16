"""Database URL handling shared by the loader and the backend (no pipeline imports, so the deployed
backend needs only dashboard/requirements.txt)."""


def normalize_url(url):
    """Accept the postgres:// / postgresql:// strings hosts hand out; use the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url
