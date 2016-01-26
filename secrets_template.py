# Copy this file into secrets.py and set keys, secrets and scopes.

# This is a session secret key used by webapp2 framework.
# Get 'a random and long string' from here:
# http://clsc.net/tools/random-string-generator.php
# or execute this from a python shell: import os; os.urandom(64)
SESSION_KEY = "key"

# Google APIs
GOOGLE_APP_ID = 'id'
GOOGLE_APP_SECRET = 'secret'

# Facebook auth apis
FACEBOOK_APP_ID = 'id'
FACEBOOK_APP_SECRET = 'secret'

# Key/secret for both LinkedIn OAuth 1.0a and OAuth 2.0
# https://www.linkedin.com/secure/developer
LINKEDIN_KEY = 'consumer key / client id'
LINKEDIN_SECRET = 'consumer secret / client secret'

# https://manage.dev.live.com/AddApplication.aspx
# https://manage.dev.live.com/Applications/Index
WL_CLIENT_ID = 'client id'
WL_CLIENT_SECRET = 'client secret'

# https://dev.twitter.com/apps
TWITTER_CONSUMER_KEY = 'oauth1.0a consumer key'
TWITTER_CONSUMER_SECRET = 'oauth1.0a consumer secret'

# https://foursquare.com/developers/apps
FOURSQUARE_CLIENT_ID = 'client id'
FOURSQUARE_CLIENT_SECRET = 'client secret'

# config that summarizes the above
AUTH_CONFIG = {
  # OAuth 2.0 providers
  'google': (GOOGLE_APP_ID, GOOGLE_APP_SECRET,
             'https://www.googleapis.com/auth/userinfo.profile'),
  'googleplus': (GOOGLE_APP_ID, GOOGLE_APP_SECRET, 'profile email'),
  'linkedin2': (LINKEDIN_KEY, LINKEDIN_SECRET, 'r_basicprofile'),
  'facebook': (FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, 'user_about_me'),
  'windows_live': (WL_CLIENT_ID, WL_CLIENT_SECRET, 'wl.signin'),
  'foursquare': (FOURSQUARE_CLIENT_ID, FOURSQUARE_CLIENT_SECRET,
                 'authorization_code'),

  # OAuth 1.0 providers don't have scopes
  'twitter': (TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET),
  'linkedin': (LINKEDIN_KEY, LINKEDIN_SECRET),

  # OpenID doesn't need any key/secret
}

AUTH_OPTIONAL_PARAMS = {
  #	Provider auth init optional parameters
  # '<provider>': {'<parameter_name>': '<value>'}
  # ex. 'twitter' : {'force_login': True}
}
