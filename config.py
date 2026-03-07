"""Configuration loader and validator.

Loads environment variables from .env and the OS, applies defaults, and
validates required settings. Provides a simple namespace for other modules.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    # WordPress settings
    wp_base_url: str
    wp_username: str
    wp_app_password: str
    wp_post_type: str
    wp_default_status: str

    # Google Search Console
    gsc_site_url: str
    google_application_credentials: str
    google_oauth_client_secrets: Optional[str]  # path or raw JSON string
    gsc_api_key: Optional[str]

    # Optional APIs
    openai_api_key: Optional[str]
    serpapi_key: Optional[str]

    # Cache settings
    cache_dir: Path
    cache_ttl_seconds: int

    # Misc
    max_generation_attempts: int


def load_config() -> Config:
    # load .env first if present
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        # if the file contains a raw JSON block for OAuth creds we want to
        # capture it even though dotenv would ignore it.  Look for first
        # balanced braces block and set as GSC_OAUTH_CLIENT_SECRETS if not
        # already defined.
        text = env_path.read_text(encoding='utf-8')
        if 'GSC_OAUTH_CLIENT_SECRETS' not in os.environ:
            # simple heuristic: find first { ... } block
            import re
            m = re.search(r'(\{[^\}]*\})', text, re.S)
            if m:
                os.environ['GSC_OAUTH_CLIENT_SECRETS'] = m.group(1)

    def get(key: str, default: Optional[str] = None, required: bool = False) -> str:
        val = os.getenv(key, default)
        if required and not val:
            print(f"[CONFIG] Missing required environment variable: {key}", file=sys.stderr)
            sys.exit(1)
        return val or ""

    cfg = Config(
        wp_base_url=get('WP_BASE_URL', 'https://localhost'),
        wp_username=get('WP_USERNAME', 'admin'),
        wp_app_password=get('WP_APP_PASSWORD', ''),
        wp_post_type=get('WP_POST_TYPE', 'posts'),
        wp_default_status=get('WP_DEFAULT_STATUS', 'draft'),

        gsc_site_url=get('GSC_SITE_URL', 'https://localhost'),
        google_application_credentials=get('GOOGLE_APPLICATION_CREDENTIALS', 'gsc-creds.json'),
        # if GSC_OAUTH_CLIENT_SECRETS contains JSON text we will handle later
        google_oauth_client_secrets=get('GSC_OAUTH_CLIENT_SECRETS', None),
        gsc_api_key=get('GSC_API_KEY', None),

        openai_api_key=get('OPENAI_API_KEY', None),
        serpapi_key=get('SERPAPI_KEY', None),

        cache_dir=Path(get('CACHE_DIR', 'data/cache')),
        cache_ttl_seconds=int(get('CACHE_TTL_SECONDS', '21600')),

        max_generation_attempts=int(get('MAX_GENERATION_ATTEMPTS', '5')),
    )

    # ensure cache dir exists
    cfg.cache_dir.mkdir(parents=True, exist_ok=True)
    return cfg


# singleton config
cfg = load_config()