"""
Custom Authenticator to use Google OAuth with JupyterHub.
Derived from the GitHub OAuth authenticator.
"""

import os
import json

from tornado             import gen
from tornado.auth        import GoogleOAuth2Mixin
from tornado.web         import HTTPError

from traitlets           import Unicode, Tuple, default, List

from jupyterhub.auth     import LocalAuthenticator
from jupyterhub.utils    import url_path_join

from .oauth2 import OAuthLoginHandler, OAuthCallbackHandler, OAuthenticator

class GoogleLoginHandler(OAuthLoginHandler, GoogleOAuth2Mixin):
    '''An OAuthLoginHandler that provides scope to GoogleOAuth2Mixin's
       authorize_redirect.'''
    def get(self):
        redirect_uri = self.authenticator.get_callback_url(self)
        self.log.info('redirect_uri: %r', redirect_uri)

        self.authorize_redirect(
            redirect_uri=redirect_uri,
            client_id=self.authenticator.client_id,
            scope=['openid', 'email'],
            response_type='code')


class GoogleOAuthHandler(OAuthCallbackHandler, GoogleOAuth2Mixin):
    pass


class GoogleOAuthenticator(OAuthenticator, GoogleOAuth2Mixin):

    login_handler = GoogleLoginHandler
    callback_handler = GoogleOAuthHandler


    login_service = Unicode(
        os.environ.get('LOGIN_SERVICE', 'Google'),
        config=True,
        help="""Google Apps hosted domain string, e.g. My College"""
    )
    
    hosted_domain = List(
    	os.environ.get('HOSTED_DOMAIN', '')
        config=True,
        help="""Tuple of hosted domains used to restrict sign-in, e.g. mycollege.edu"""
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

        domain_list = list(hosted_domain)

        if domain_list
            found = False
            for domain in domain_list:
                if username.endswith('@'+domain) or bodyjs['hd'] == domain:
                    found = True
                    username = username.split('@')[0]
            if found is False:
                raise HTTPError(403, "You are not signed in to your university account.")
        return username

        """if self.hosted_domains:
            print(str(self.hosted_domains))
            username, _, domain = username.partition('@')
            if not domain in self.hosted_domains or \
                bodyjs['hd'] not in self.hosted_domains:
                raise HTTPError(403,
                    "You are not signed in to your {} account.".format(
                        domain)
                )

        return username"""

class LocalGoogleOAuthenticator(LocalAuthenticator, GoogleOAuthenticator):
    """A version that mixes in local system user creation"""
    pass