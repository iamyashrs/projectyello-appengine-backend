import webapp2
import sys
from datetime import datetime
import wsgiref.handlers
from webapp2 import Route

from secrets import SESSION_KEY

# inject './lib' dir in the path so that we can simply do "import ndb"
# or whatever there's in the app lib dir.
if 'lib' not in sys.path:
    sys.path[0:0] = ['lib']


def nickname(s):
    return s.split("@")[0]


def timesince(value, default="just now"):
    now = datetime.utcnow()
    diff = now - value
    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )
    for period, singular, plural in periods:
        if period:
            return "%d %s ago" % (period, singular if period == 1 else plural)
    return default


# webapp2 config
app_config = {
    'webapp2_extras.sessions': {
        'cookie_name': '_simpleauth_sess',
        'secret_key': SESSION_KEY
    },
    'webapp2_extras.auth': {
        'user_attributes': []
    },
    'webapp2_extras.jinja2': {
        'filters': {'timesince': timesince,
                    'nickname': nickname}
    }
}

routes = [
    Route('/', handler='handlers.MainHandler', name='MainHandler'),
    Route('/vote/', handler='handlers.VoteHandler', name='VoteHandler'),
    Route('/post/<quoteid:\d+>', handler='handlers.QuoteHandler', name='QuoteHandler'),
    Route('/top', handler='handlers.TopHandler', name='TopHandler'),
    Route('/image_post', handler='handlers.UploadPicture', name='UploadPicture'),
    Route('/submit', handler='handlers.SubmitHandler', name='SubmitHandler'),
    Route('/add_comment', handler='handlers.CommentHandler', name='CommentHandler'),
    Route('/del_comment/<commentid:\d+>', handler='handlers.CommentDeleterHandler', name='CommentDeleteHandler'),
    Route('/search', handler='handlers.SearchHandler', name='SearchHandler'),

    Route('/logout', handler='handlers.AuthHandler:logout', name='logout'),
    Route('/auth/<provider>', handler='handlers.AuthHandler:_simple_auth', name='auth_login'),
    Route('/auth/<provider>/callback', handler='handlers.AuthHandler:_auth_callback', name='auth_callback'),
]

application = webapp2.WSGIApplication(routes, config=app_config, debug=True)


def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
