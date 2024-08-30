"""Basic scaffolding for handling OAuth"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/08_oauth.ipynb.

# %% auto 0
__all__ = ['GoogleAppClient', 'GitHubAppClient', 'HuggingFaceClient', 'DiscordAppClient', 'decode', 'OAuth']

# %% ../nbs/api/08_oauth.ipynb
from .common import *
from oauthlib.oauth2 import WebApplicationClient
from urllib.parse import urlparse, urlencode, parse_qs, quote, unquote
from httpx import get, post
import secrets

# %% ../nbs/api/08_oauth.ipynb
class _AppClient(WebApplicationClient):
    def __init__(self, client_id, client_secret, code=None, scope=None, **kwargs):
        super().__init__(client_id, code=code, scope=scope, **kwargs)
        self.client_secret = client_secret

# %% ../nbs/api/08_oauth.ipynb
class GoogleAppClient(_AppClient):
    "A `WebApplicationClient` for Google oauth2"
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://www.googleapis.com/oauth2/v4/token"
    info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    id_key = 'sub'
    
    def __init__(self, client_id, client_secret, code=None, scope=None, **kwargs):
        scope_pre = "https://www.googleapis.com/auth/userinfo"
        if not scope: scope=["openid", f"{scope_pre}.email", f"{scope_pre}.profile"]
        super().__init__(client_id, client_secret, code=code, scope=scope, **kwargs)
    
    @classmethod
    def from_file(cls, fname, code=None, scope=None, **kwargs):
        cred = Path(fname).read_json()['web']
        return cls(cred['client_id'], client_secret=cred['client_secret'], code=code, scope=scope, **kwargs)

# %% ../nbs/api/08_oauth.ipynb
class GitHubAppClient(_AppClient):
    "A `WebApplicationClient` for GitHub oauth2"
    base_url = "https://github.com/login/oauth/authorize"
    token_url = "https://github.com/login/oauth/access_token"
    info_url = "https://api.github.com/user"
    id_key = 'id'

    def __init__(self, client_id, client_secret, code=None, scope=None, **kwargs):
        if not scope: scope="user"
        super().__init__(client_id, client_secret, code=code, scope=scope, **kwargs)

# %% ../nbs/api/08_oauth.ipynb
class HuggingFaceClient(_AppClient):
    "A `WebApplicationClient` for HuggingFace oauth2"

    base_url = "https://huggingface.co/oauth/authorize"
    token_url = "https://huggingface.co/oauth/token"
    info_url = "https://huggingface.co/oauth/userinfo"
    id_key = 'sub'
    
    def __init__(self, client_id, client_secret, code=None, scope=None, state=None, **kwargs):
        if not scope: scope=["openid","profile"]
        if not state: state=secrets.token_urlsafe(16)
        super().__init__(client_id, client_secret, code=code, scope=scope, state=state, **kwargs)

# %% ../nbs/api/08_oauth.ipynb
class DiscordAppClient(_AppClient):
    "A `WebApplicationClient` for Discord oauth2"
    base_url = "https://discord.com/oauth2/authorize"
    token_url = "https://discord.com/api/oauth2/token"
    revoke_url = "https://discord.com/api/oauth2/token/revoke"
    id_key = 'id'

    def __init__(self, client_id, client_secret, is_user=False, perms=0, scope=None, **kwargs):
        if not scope: scope="applications.commands applications.commands.permissions.update identify"
        self.integration_type = 1 if is_user else 0
        self.perms = perms
        super().__init__(client_id, client_secret, scope=scope, **kwargs)

    def login_link(self):
        d = dict(response_type='code', client_id=self.client_id,
                 integration_type=self.integration_type, scope=self.scope) #, permissions=self.perms, prompt='consent')
        return f'{self.base_url}?' + urlencode(d)

    def parse_response(self, code):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = dict(grant_type='authorization_code', code=code)#, redirect_uri=self.redirect_uri)
        r = post(self.token_url, data=data, headers=headers, auth=(self.client_id, self.client_secret))
        r.raise_for_status()
        self.parse_request_body_response(r.text)

# %% ../nbs/api/08_oauth.ipynb
@patch
def login_link(self:WebApplicationClient, redirect_uri, scope=None, state=None):
    "Get a login link for this client"
    if not scope: scope=self.scope
    if not state: state=getattr(self, 'state', None)
    return self.prepare_request_uri(self.base_url, redirect_uri, scope, state=state)

# %% ../nbs/api/08_oauth.ipynb
@patch
def parse_response(self:_AppClient, code, redirect_uri):
    "Get the token from the oauth2 server response"
    payload = dict(code=code, redirect_uri=redirect_uri, client_id=self.client_id,
                   client_secret=self.client_secret, grant_type='authorization_code')
    r = post(self.token_url, json=payload)
    r.raise_for_status()
    self.parse_request_body_response(r.text)

# %% ../nbs/api/08_oauth.ipynb
def decode(code_url):
    parsed_url = urlparse(code_url)
    query_params = parse_qs(parsed_url.query)
    return query_params.get('code', [''])[0], query_params.get('state', [''])[0], code_url.split('?')[0]

# %% ../nbs/api/08_oauth.ipynb
@patch
def get_info(self:_AppClient, token=None):
    "Get the info for authenticated user"
    if not token: token = self.token["access_token"]
    headers = {'Authorization': f'Bearer {token}'}
    return get(self.info_url, headers=headers).json()

# %% ../nbs/api/08_oauth.ipynb
@patch
def retr_info(self:_AppClient, code, redirect_uri):
    "Combines `parse_response` and `get_info`"
    self.parse_response(code, redirect_uri)
    return self.get_info()

# %% ../nbs/api/08_oauth.ipynb
@patch
def retr_id(self:_AppClient, code, redirect_uri):
    "Call `retr_info` and then return id/subscriber value"
    return self.retr_info(code, redirect_uri)[self.id_key]

# %% ../nbs/api/08_oauth.ipynb
class OAuth:
    def __init__(self, app, cli, skip=None, redir_path='/redirect', logout_path='/logout', login_path='/login'):
        if not skip: skip = [redir_path,login_path]
        self.app,self.cli,self.skip,self.redir_path,self.logout_path,self.login_path = app,cli,skip,redir_path,logout_path,login_path

        def before(req, session):
            auth = req.scope['auth'] = session.get('auth')
            if not auth: return RedirectResponse(self.login_path, status_code=303)
            info = AttrDictDefault(cli.get_info(auth))
            if not self._chk_auth(info): return RedirectResponse(self.login_path, status_code=303)
        app.before.append(Beforeware(before, skip=skip))

        @app.get(redir_path)
        def redirect(code:str, req, session, state:str=None):
            if not code: return "No code provided!"
            base_url = f"{req.url.scheme}://{req.url.netloc}"
            print(base_url)
            info = AttrDictDefault(cli.retr_info(code, base_url+redir_path))
            if not self._chk_auth(info): return RedirectResponse(self.login_path, status_code=303)
            session['auth'] = cli.token['access_token']
            return self.login(info, state)

        @app.get(logout_path)
        def logout(session):
            session.pop('auth', None)
            return self.logout(session)

    def redir_url(self, req): return f"{req.url.scheme}://{req.url.netloc}{self.redir_path}"
    def login_link(self, req): return self.cli.login_link(self.redir_url(req))

    def login(self, info, state): raise NotImplementedError()
    def logout(self, session): return RedirectResponse(self.login_path, status_code=303)
    def chk_auth(self, info, ident): raise NotImplementedError()
    def _chk_auth(self, info):
        ident = info.get(self.cli.id_key)
        return ident and self.chk_auth(info, ident)
