import os
from config import load_config, cfg

def test_oauth_secrets_from_env(tmp_path, monkeypatch):
    # create a temporary .env with JSON block
    env_file = tmp_path / ".env"
    env_file.write_text("""OPENAI_API_KEY=foo
GSC_OAUTH_CLIENT_SECRETS=not-used
{"installed":{"client_id":"abc","client_secret":"xyz"}}
""")
    monkeypatch.setenv('DOTENV_PATH', str(env_file))  # not used but ensure path
    # monkeypatch current file location
    monkeypatch.chdir(tmp_path)
    # reload config module
    import importlib
    import config as confmod
    importlib.reload(confmod)
    conf = confmod.load_config()
    assert conf.google_oauth_client_secrets.strip().startswith('{')
