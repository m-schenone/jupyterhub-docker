"""
Custom Authenticator to use Google OAuth with JupyterHub.

Derived from the GitHub OAuth authenticator.
"""

import os
import json

from tornado             import gen
from tornado.auth        import GoogleOAuth2Mixin
from tornado.web         import HTTPError

from traitlets           import Unicode

from jupyterhub.auth     import LocalAuthenticator
from jupyterhub.utils    import url_path_join

from .oauth2 import OAuthLoginHandler, OAuthCallbackHandler, OAuthenticator

class GoogleLoginHandler(OAuthLoginHandler, GoogleOAuth2Mixin):
    '''An OAuthLoginHandler that provides scope to GoogleOAuth2Mixin's
       authorize_redirect.'''
    scope = ['openid', 'email']


class GoogleOAuthHandler(OAuthCallbackHandler, GoogleOAuth2Mixin):
    pass


class GoogleOAuthenticator(OAuthenticator, GoogleOAuth2Mixin):

    login_handler = GoogleLoginHandler
    callback_handler = GoogleOAuthHandler

    hosted_domain = Unicode(
        os.environ.get('HOSTED_DOMAIN', ''),
        config=True,
        help="""Hosted domain used to restrict sign-in, e.g. mycollege.edu"""
    )
    login_service = Unicode(
        os.environ.get('LOGIN_SERVICE', 'Google'),
        config=True,
        help="""Google Apps hosted domain string, e.g. My College"""
    )

    @gen.coroutine
    def authenticate(self, handler, data=None):
        code = handler.get_argument("code")
        handler.settings['google_oauth'] = {
            'key': self.client_id,
            'secret': self.client_secret,
            'scope': ['openid', 'email']
        }
        user = yield handler.get_authenticated_user(
            redirect_uri=self.get_callback_url(handler),
            code=code)
        access_token = str(user['access_token'])

        http_client = handler.get_auth_http_client()

        response = yield http_client.fetch(
            self._OAUTH_USERINFO_URL + '?access_token=' + access_token
        )

        if not response:
            self.clear_all_cookies()
            raise HTTPError(500, 'Google authentication failed')

        body = response.body.decode()
        self.log.debug('response.body.decode(): {}'.format(body))
        bodyjs = json.loads(body)

        username = bodyjs['email']

        if username is None or username == "":
            raise HTTPError(403, "DEBUG: username is null or empty")

        domains = ['ateneopv.it', 'unipv.it', 'universitadipavia.it']
        is_in_domain = any([username.endswith('@'+domain) for domain in domains])

        username = username.split('@')[0]

        if is_in_domain:
            return username

        if bodyjs is None or 'hd' not in bodyjs:
            raise HTTPError(403, "You are not signed in any unipv account.")

        is_bodyjs_in_domain = any([bodyjs['hd'] == domain for domain in domains])

        if not is_bodyjs_in_domain:
            raise HTTPError(403, "You are not signed in any unipv account.")

        return username

class LocalGoogleOAuthenticator(LocalAuthenticator, GoogleOAuthenticator):
    """A version that mixes in local system user creation"""
    pass