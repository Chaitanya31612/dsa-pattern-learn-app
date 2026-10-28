"""Cloudflare entry point; routes and teaching logic stay in app.py."""
from workers import asgi
from app import app, load_db
from cloudflare_adapter import HostedAPI
from hld_api import catalog as hld_catalog
from software_api import catalog as software_catalog
from ai_learning_api import ai_catalog

# Populate the original read-only caches during Worker initialization, rather
# than parsing whole catalogs inside the free plan's per-request CPU budget.
for load in (load_db, hld_catalog, software_catalog, ai_catalog):
    load()

Default = asgi.entrypoint(HostedAPI(app))
