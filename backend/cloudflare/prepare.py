"""Package the original API, without .env, virtualenvs, tests, or scraping tools."""
from pathlib import Path
import json
import os
import shutil

BACKEND = Path(__file__).resolve().parents[1]
CONFIG = BACKEND / 'cloudflare'
BUILD = BACKEND / '.cloudflare'


def prepare():
    source = BUILD / 'src'
    # Only the generated source subtree is replaced; cached Python tooling stays.
    if source.exists():
        shutil.rmtree(source)
    source.mkdir(parents=True)
    for name in ('worker.py', 'cloudflare_adapter.py', 'app.py', 'hld_api.py', 'software_api.py', 'ai_learning_api.py'):
        shutil.copy2(BACKEND / name, source / name)
    (source / 'ai').mkdir()
    for path in (BACKEND / 'ai').glob('*.py'):
        shutil.copy2(path, source / 'ai' / path.name)
    data = source / 'pipeline/data'
    data.mkdir(parents=True)
    for name in ('db.json', 'hld-course.json', 'software-course.json', 'ai-course.json'):
        shutil.copy2(BACKEND / 'pipeline/data' / name, data / name)
    for name in ('pyproject.toml', 'uv.lock', 'pylock.toml'):
        shutil.copy2(CONFIG / name, BUILD / name)
    # Keep account-specific browser origins outside tracked configuration.
    config = json.loads((CONFIG / 'wrangler.jsonc').read_text())
    local_config = CONFIG / 'wrangler.local.json'
    if local_config.exists():
        overrides = json.loads(local_config.read_text())
        if set(overrides) - {'vars'} or not isinstance(overrides.get('vars', {}), dict):
            raise ValueError('Local Worker configuration supports only a vars object.')
        variables = overrides.get('vars', {})
        if set(variables) - {'ALLOWED_ORIGINS', 'AI_REQUESTS_PER_MINUTE'}:
            raise ValueError('Keep secrets out of configuration; use Cloudflare runtime secrets.')
        config['vars'].update(variables)
    # CI can supply its origins in build settings without committing site names.
    if os.environ.get('CLOUDFLARE_ALLOWED_ORIGINS'):
        config['vars']['ALLOWED_ORIGINS'] = os.environ['CLOUDFLARE_ALLOWED_ORIGINS']
    (BUILD / 'wrangler.jsonc').write_text(json.dumps(config, indent=2) + '\n')
    # Only an explicitly created local Worker secret file is used. Production
    # secrets are configured in Cloudflare, and backend/.env is never bundled.
    secret = CONFIG / '.dev.vars'
    if secret.exists():
        shutil.copy2(secret, BUILD / '.dev.vars')
        (BUILD / '.dev.vars').chmod(0o600)
    else:
        (BUILD / '.dev.vars').unlink(missing_ok=True)
    print('Packaged the original API in backend/.cloudflare/src (no .env or pipeline scripts).')
    return BUILD


if __name__ == '__main__':
    prepare()
