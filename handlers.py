import logging
from urlparse import parse_qs
from urlparse import urlparse

import webapp2
import webob.multidict
from webapp2_extras import auth, sessions, jinja2
from jinja2.runtime import TemplateNotFound
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import images

import secrets
import modals
from lib.simpleauth import SimpleAuthHandler

DEFAULT_AVATAR_URL = '/images/missing_avatar.png'
FACEBOOK_AVATAR_URL = 'https://graph.facebook.com/{0}/picture?type=large'


class BaseRequestHandler(webapp2.RequestHandler):
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)

        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def jinja2(self):
        """Returns a Jinja2 renderer cached in the app registry"""
        return jinja2.get_jinja2(app=self.app)

    @webapp2.cached_property
    def session(self):
        """Returns a session using the default cookie key"""
        return self.session_store.get_session()

    @webapp2.cached_property
    def auth(self):
        return auth.get_auth()

    @webapp2.cached_property
    def current_user(self):
        """Returns currently logged in user"""
        user_dict = self.auth.get_user_by_session()
        return self.auth.store.user_model.get_by_id(user_dict['user_id'])

    @webapp2.cached_property
    def logged_in(self):
        """Returns true if a user is currently logged in, false otherwise"""
        return self.auth.get_user_by_session() is not None

    def render(self, template_name, template_vars={}):
        # Preset values for the template
        values = {
            'url_for': self.uri_for,
            'logged_in': self.logged_in,
            'flashes': self.session.get_flashes()
        }

        # Add manually supplied template values
        values.update(template_vars)

        # read the template or 404.html
        try:
            self.response.write(self.jinja2.render_template(template_name, **values))
        except TemplateNotFound:
            self.abort(404)

    def head(self, *args):
        """Head is used by Twitter. If not there the tweet button shows 0"""
        pass


def quote_for_template(quotes, user, page=0):
    quotes_tpl = []
    index = 1 + page * modals.PAGE_SIZE
    for quote in quotes:
        quotes_tpl.append({
            'id': quote.key.id(),
            'title': quote.title,
            'uri': quote.uri,
            'made_on': quote.made_on,
            'voted': modals.voted(quote, user),
            'quote': quote.quote,
            'images': images.get_serving_url,
            'image': quote.image,
            'comments': quote.comments,
            'creator': quote.creator,
            'creator_anonymous': quote.creator_anonymous,
            'created': quote.creation_order[:10],
            'created_long': quote.creation_order[:19],
            'votesum': quote.votesum,
            'index': index
        })
        index += 1
    return quotes_tpl


def create_template_dict(user, quotes, section, title, nexturi=None, prevuri=None, page=0):
    template_values = {
        'title': title,
        'user': user,
        'quotes': quote_for_template(quotes, user, page),
        'section': section,
        'images': images.get_serving_url,
        'nexturi': nexturi,
        'prevuri': prevuri
    }

    return template_values


def create_template_dict_main(user, quotes, section, quotesr, sectionr, nexturi=None, prevuri=None, page=0,
                              nexturir=None, prevurir=None):
    upload_url = blobstore.create_upload_url('/image_post')
    template_values = {
        'title': 'Project Yello | JUET, Guna',
        'user': user,
        'quotes': quote_for_template(quotes, user, page),
        'section': section,
        'upload_url': upload_url,
        'nexturi': nexturi,
        'images': images.get_serving_url,
        'prevuri': prevuri,
        'quotesr': quote_for_template(quotesr, user, page),
        'sectionr': sectionr,
        'nexturir': nexturir,
        'prevurir': prevurir,
        'destination_url': '/'
    }

    return template_values


def create_template_dict_single_quote(user, quotes, section, comments, nexturi=None, prevuri=None, page=0):
    quote_id = 1
    quote_title = ''
    for quote in quotes:
        quote_id = quote.key.id()
        quote_title = quote.title

    template_values = {
        'title': 'Post - ' + quote_title,
        'user': user,
        'comments': comments,
        'quote_id': quote_id,
        'images': images.get_serving_url,
        'quotes': quote_for_template(quotes, user, page),
        'section': section,
        'nexturi': nexturi,
        'prevuri': prevuri
    }

    return template_values


class VoteHandler(BaseRequestHandler):
    def post(self):
        if self.logged_in:
            user = self.current_user
            quoteid = self.request.get('quoteid')
            vote = self.request.get('vote')
            if not vote in ['1', '-1']:
                self.response.set_status(400, 'Bad Request')
                return
            vote = int(vote)
            modals.set_vote(long(quoteid), user, vote, provider=user.provider)
        else:
            self.response.set_status(403, 'Forbidden')
            return


class QuoteHandler(BaseRequestHandler):
    def post(self, quoteid):
        if self.logged_in:
            user = self.current_user
            modals.del_quote(long(quoteid), user)
            self.redirect('/')
        else:
            self.response.set_status(403, 'Forbidden')
            return

    def get(self, quoteid):
        quote = modals.get_quote(long(quoteid))
        if quote is None:
            self.response.set_status(404, 'Not Found')
            return
        quotes = [quote]
        comments = modals.get_comments(quoteid)

        if self.logged_in:
            user = self.current_user
            template_values = create_template_dict_single_quote(user, quotes, 'Quote', comments, nexturi=None,
                                                                prevuri=None, page=0)
        else:
            template_values = create_template_dict_single_quote(None, quotes, 'Quote', comments, nexturi=None,
                                                                prevuri=None, page=0)

        self.render('singlequote.html', template_values)


class MainHandler(BaseRequestHandler):
    def get(self):
        page = int(self.request.get('p', '0'))
        quotes, next = modals.get_quotes(page)
        if next:
            nexturi = '/?p=%d' % (page + 1)
        else:
            nexturi = None
        if page > 1:
            prevuri = '/?p=%d' % (page - 1)
        elif page == 1:
            prevuri = '/'
        else:
            prevuri = None

        offset = self.request.get('offset')
        pager = int(self.request.get('p', '0'))
        if not offset:
            offset = None
        quotesr, nextr = modals.get_quotes_newest(offset)
        if nextr:
            nexturir = '?offset=%s&p=%d' % (next, page + 1)
        else:
            nexturir = None

        if self.logged_in:
            user = self.current_user
            template_values = create_template_dict_main(
                    user, quotes, 'Popular', quotesr, 'Recent', nexturi, prevuri, pager, nexturir, None
            )
        else:
            template_values = create_template_dict_main(
                    None, quotes, 'Popular', quotesr, 'Recent', nexturi, prevuri, pager, nexturir, None
            )

        self.render('index.html', template_values)

    def post(self):
        if self.logged_in:
            user = self.current_user
            title = self.request.get('title')
            if str(self.request.get('anon')) == "on":
                anon = False
            else:
                anon = True
            text = self.request.get('quote').strip()
            if len(text) > 500:
                text = text[:500]
            if len(title) > 75:
                title = title[:75]
            uri = self.request.get('url').strip()
            parsed_uri = urlparse(uri)

            if uri and (not parsed_uri.scheme or not parsed_uri.netloc):
                template_values = {
                    'user': user,
                    'title': title,
                    'text': text,
                    'uri': uri,
                    'error_msg': 'The supplied link is not a valid absolute URI'
                }
                self.render('add_quote_error.html', template_values)

            else:
                if len(title) != 0 and title is not None:
                    quote_id = modals.add_quote(title1=title, user_id=user, user_anon=anon, provider=user.provider,
                                                quote1=text, url1=uri)
                    if quote_id is not None:
                        modals.set_vote(long(quote_id), user, 1, provider=user.provider)
                        self.redirect('/')
                    else:
                        template_values = {
                            'user': user,
                            'title': title,
                            'text': text,
                            'uri': uri,
                            'error_msg': 'An error occured while adding this quote, please try again.'
                        }

                        self.render('add_quote_error.html', template_values)
                else:
                    template_values = {
                        'user': user,
                        'title': title,
                        'text': text,
                        'uri': uri,
                        'error_msg': 'An error occured while adding this quote, please try again. you forgot to enter title.'
                    }

                    self.render('add_quote_error.html', template_values)

        else:
            self.response.set_status(403, 'Forbidden')
            return


class UploadPicture(blobstore_handlers.BlobstoreUploadHandler, BaseRequestHandler):
    def post(self):
        if self.logged_in:
            user = self.current_user
            title = self.request.get('title')
            if str(self.request.get('anon')) == "on":
                anon = False
            else:
                anon = True
            text = self.request.get('quote').strip()
            if len(text) > 500:
                text = text[:500]
            if len(title) > 75:
                title = title[:75]
            uri = self.request.get('url').strip()
            parsed_uri = urlparse(uri)

            if uri and (not parsed_uri.scheme or not parsed_uri.netloc):
                template_values = {
                    'user': user,
                    'title': title,
                    'text': text,
                    'uri': uri,
                    'error_msg': 'The supplied link is not a valid absolute URI'
                }

                self.render('add_quote_error.html', template_values)

            else:
                image = self.get_uploads('image')
                type = image[0].content_type

                if image and type.startswith('image/') and len(title) != 0:
                    blob_info = image[0]
                    image = blob_info.key()

                    quote_id = modals.add_quote(title1=title, user_id=user, user_anon=anon, provider=user.provider,
                                                quote1=text, url1=uri, image=image)
                    if quote_id is not None:
                        modals.set_vote(long(quote_id), user, 1, provider=user.provider)
                        self.redirect('/')
                    else:
                        template_values = {
                            'user': user,
                            'title': title,
                            'text': text,
                            'uri': uri,
                            'error_msg': 'An error occured while adding this quote, please try again.'
                        }

                        self.render('add_quote_error.html', template_values)
                else:
                    blob_info = image[0]
                    image = blob_info.key()
                    blobstore.delete(image)
                    self.redirect('/')
        else:
            self.response.set_status(403, 'Forbidden')
            return


class TopHandler(BaseRequestHandler):
    def get(self):
        page = int(self.request.get('p', '0'))
        quotes, next = modals.get_quotes_top(page)
        if next:
            nexturi = '/?p=%d' % (page + 1)
        else:
            nexturi = None
        if page > 1:
            prevuri = '/?p=%d' % (page - 1)
        elif page == 1:
            prevuri = '/'
        else:
            prevuri = None
        section = 'top'

        if self.logged_in:
            user = self.current_user
            template_values = create_template_dict(user, quotes, section, 'Top Posts - ProjectYello', nexturi, prevuri,
                                                   page)
        else:
            template_values = create_template_dict(None, quotes, section, 'Top Posts - ProjectYello', nexturi, prevuri,
                                                   page)

        self.render('top.html', template_values)


class SubmitHandler(BaseRequestHandler):
    def get(self):
        if self.logged_in:
            upload_url = blobstore.create_upload_url('/image_post')
            template_values = {
                'user': self.current_user,
                'title': "Submit - ProjectYello",
                'upload_url': upload_url,
            }
        else:
            template_values = {
                'user': None,
                'title': "Submit - ProjectYello",
            }

        self.render('submit.html', template_values)


class SearchHandler(BaseRequestHandler):
    def get(self):
        uri = urlparse(self.request.uri)
        query = 'null'
        if uri.query:
            query = parse_qs(uri.query)
            query = query['query'][0]

        if query is not 'null':
            page = int(self.request.get('p', '0'))
            quotes, next = modals.get_search_results(query, page)
            if next:
                nexturi = '/?p=%d' % (page + 1)
            else:
                nexturi = None
            if page > 1:
                prevuri = '/?p=%d' % (page - 1)
            elif page == 1:
                prevuri = '/'
            else:
                prevuri = None
            section = 'search'

            if self.logged_in:
                user = self.current_user
                template_values = create_template_dict(user, quotes, section, 'Search - ' + query, nexturi, prevuri,
                                                       page)
            else:
                template_values = create_template_dict(None, quotes, section, 'Search - ' + query, nexturi, prevuri,
                                                       page)

        else:
            if self.logged_in:
                template_values = {
                    'title': "Search - ProjectYello",
                    'user': self.current_user,
                }
            else:
                template_values = {
                    'title': "Search - ProjectYello",
                    'user': None,
                }

        self.render('search.html', template_values)


class CommentHandler(BaseRequestHandler):
    def post(self):
        if self.logged_in:
            user = self.current_user
            quoteid = self.request.get('quoteid')
            text = self.request.get('comment')
            if str(self.request.get('anon')) == "on":
                anon = False
            else:
                anon = True

            modals.add_comment(user=user, user_anon=anon, quote_id=quoteid, text=text, provider=user.provider)
            self.redirect('/post/' + quoteid)

        else:
            self.response.set_status(403, 'Forbidden')
            return


class CommentDeleterHandler(BaseRequestHandler):
    def post(self, commentid):
        if self.logged_in:
            quoteid = self.request.get('quoteid')

            user = self.current_user
            modals.del_comment(quoteid, commentid, user)
            self.redirect('/post/' + quoteid)
        else:
            self.response.set_status(403, 'Forbidden')
            return


class AuthHandler(BaseRequestHandler, SimpleAuthHandler):
    """Authentication handler for OAuth 2.0, 1.0(a) and OpenID."""

    # Enable optional OAuth 2.0 CSRF guard
    OAUTH2_CSRF_STATE = True

    USER_ATTRS = {
        'facebook': {
            'id': lambda id: ('avatar_url', FACEBOOK_AVATAR_URL.format(id)),
            'name': 'name',
            'link': 'link',
            'email': 'email',
        },
        'google': {
            'picture': 'avatar_url',
            'name': 'name',
            'profile': 'link',
            'email': 'email',
        },
        'googleplus': {
            'image': lambda img: ('avatar_url', img.get('url', DEFAULT_AVATAR_URL)),
            'displayName': 'name',
            'url': 'link',
            'emails': lambda email: ('email', email[0].get('value')),
        },
        'windows_live': {
            'avatar_url': 'avatar_url',
            'name': 'name',
            'link': 'link',
        },
        'twitter': {
            'profile_image_url': 'avatar_url',
            'screen_name': 'name',
            'link': 'link',
        },
        'linkedin': {
            'picture-url': 'avatar_url',
            'first-name': 'name',
            'public-profile-url': 'link',
        },
        'linkedin2': {
            'picture-url': 'avatar_url',
            'first-name': 'name',
            'public-profile-url': 'link',
        },
        'foursquare': {
            'photo': lambda photo: ('avatar_url', photo.get('prefix') + '100x100' \
                                    + photo.get('suffix')),
            'firstName': 'firstName',
            'lastName': 'lastName',
            'contact': lambda contact: ('email', contact.get('email')),
            # 'id': lambda id: ('link', FOURSQUARE_USER_LINK.format(id))
        },
        'openid': {
            'id': lambda id: ('avatar_url', DEFAULT_AVATAR_URL),
            'nickname': 'name',
            'email': 'link',
        }
    }

    def _on_signin(self, data, auth_info, provider, extra=None):
        """Callback whenever a new or existing user is logging in.
     data is a user info dictionary.
     auth_info contains access token or oauth token and secret.
     extra is a dict with additional params passed to the auth init handler.
    """
        logging.debug('Got user data: %s', data)

        auth_id = '%s:%s' % (provider, data['id'])

        logging.debug('Looking for a user with id %s', auth_id)
        user = self.auth.store.user_model.get_by_auth_id(auth_id)
        _attrs = self._to_user_model_attrs(data, self.USER_ATTRS[provider])

        if user:
            logging.debug('Found existing user to log in')
            # Existing users might've changed their profile data so we update our
            # local model anyway. This might result in quite inefficient usage
            # of the Datastore, but we do this anyway for demo purposes.
            #
            # In a real app you could compare _attrs with user's properties fetched
            # from the datastore and update local user in case something's changed.
            user.populate(**_attrs)
            user.put()
            self.auth.set_session(self.auth.store.user_to_dict(user))

        else:
            # check whether there's a user currently logged in
            # then, create a new user if nobody's signed in,
            # otherwise add this auth_id to currently logged in user.

            if self.logged_in:
                logging.debug('Updating currently logged in user')

                u = self.current_user
                u.populate(**_attrs)
                # The following will also do u.put(). Though, in a real app
                # you might want to check the result, which is
                # (boolean, info) tuple where boolean == True indicates success
                # See webapp2_extras.appengine.auth.models.User for details.
                u.add_auth_id(auth_id)

            else:
                logging.debug('Creating a brand new user')
                _attrs['provider'] = provider
                ok, user = self.auth.store.user_model.create_user(auth_id, **_attrs)
                if ok:
                    self.auth.set_session(self.auth.store.user_to_dict(user))

        # Remember auth data during redirect, just for this demo. You wouldn't
        # normally do this.
        self.session.add_flash(auth_info, 'auth_info')
        self.session.add_flash({'extra': extra}, 'extra')

        # user profile page
        destination_url = '/'
        if extra is not None:
            params = webob.multidict.MultiDict(extra)
            destination_url = str(params.get('destination_url', '/'))
        return self.redirect(destination_url)

    def logout(self):
        self.auth.unset_session()
        self.redirect('/')

    def handle_exception(self, exception, debug):
        logging.error(exception)
        self.render('error.html', {'exception': exception})

    def _callback_uri_for(self, provider):
        return self.uri_for('auth_callback', provider=provider, _full=True)

    def _get_consumer_info_for(self, provider):
        """Returns a tuple (key, secret) for auth init requests."""
        return secrets.AUTH_CONFIG[provider]

    def _get_optional_params_for(self, provider):
        """Returns optional parameters for auth init requests."""
        return secrets.AUTH_OPTIONAL_PARAMS.get(provider)

    def _to_user_model_attrs(self, data, attrs_map):
        """Get the needed information from the provider dataset."""
        user_attrs = {}
        for k, v in attrs_map.iteritems():
            attr = (v, data.get(k)) if isinstance(v, str) else v(data.get(k))
            user_attrs.setdefault(*attr)

        return user_attrs
