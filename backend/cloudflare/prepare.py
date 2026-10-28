"""Package the original API, without .env, virtualenvs, tests, or scraping tools."""
from pathlib import Path
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
    for name in ('pyproject.toml', 'uv.lock', 'pylock.toml', 'wrangler.jsonc'):
        shutil.copy2(CONFIG / name, BUILD / name)
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
