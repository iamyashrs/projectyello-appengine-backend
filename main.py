import jinja2
import os
import webapp2
import cgi
import modals
import wsgiref.handlers
from datetime import datetime
from urlparse import parse_qs
from urlparse import urlparse

from google.appengine.api import users
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import images

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


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


jinja_environment.filters['timesince'] = timesince


def get_greeting():
    user = users.get_current_user()
    if user:
        greeting = ('%s (<a class="loggedin" href="%s">sign out</a>)' %
                    (user.nickname(), cgi.escape(users.create_logout_url('/'))))
    else:
        greeting = ("""<a  href=\"%s\">Sign in to vote or submit
        your own post</a>.""" % cgi.escape(users.create_login_url("/")))
    return greeting


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
            'created': quote.creation_order[:10],
            'created_long': quote.creation_order[:19],
            'votesum': quote.votesum,
            'index': index
        })
        index += 1
    return quotes_tpl


def create_template_dict(user, quotes, section, nexturi=None, prevuri=None, page=0):
    greeting = get_greeting()
    template_values = {
        'loggedin': user,
        'quotes': quote_for_template(quotes, user, page),
        'section': section,
        'images': images.get_serving_url,
        'greeting': greeting,
        'nexturi': nexturi,
        'prevuri': prevuri
    }

    return template_values


def create_template_dict_main(user, quotes, section, quotesr, sectionr, nexturi=None, prevuri=None, page=0,
                              nexturir=None, prevurir=None):
    greeting = get_greeting()
    upload_url = blobstore.create_upload_url('/image_post')
    template_values = {
        'loggedin': user,
        'quotes': quote_for_template(quotes, user, page),
        'section': section,
        'upload_url': upload_url,
        'nexturi': nexturi,
        'images': images.get_serving_url,
        'prevuri': prevuri,
        'greeting': greeting,
        'quotesr': quote_for_template(quotesr, user, page),
        'sectionr': sectionr,
        'nexturir': nexturir,
        'prevurir': prevurir
    }

    return template_values


def create_template_dict_single_quote(user, quotes, section, comments, nexturi=None, prevuri=None, page=0):
    greeting = get_greeting()
    quote_id = 1
    for quote in quotes:
        quote_id = quote.key.id()

    template_values = {
        'loggedin': user,
        'comments': comments,
        'quote_id': quote_id,
        'images': images.get_serving_url,
        'quotes': quote_for_template(quotes, user, page),
        'section': section,
        'greeting': greeting,
        'nexturi': nexturi,
        'prevuri': prevuri
    }

    return template_values


class VoteHandler(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()
        if None == user:
            self.response.set_status(403, 'Forbidden')
            return
        quoteid = self.request.get('quoteid')
        vote = self.request.get('vote')
        if not vote in ['1', '-1']:
            self.response.set_status(400, 'Bad Request')
            return
        vote = int(vote)
        modals.set_vote(long(quoteid), user, vote)


class FeedHandler(webapp2.RequestHandler):
    def get(self, section):
        user = None
        if section == 'recent':
            quotes, next = modals.get_quotes_newest()
        elif section == 'popular':
            quotes, next = modals.get_quotes()
        else:
            self.response.set_status(404, 'Not Found')
            return

        template_values = create_template_dict(user, quotes, section.capitalize())
        self.response.headers['Content-Type'] = 'application/atom+xml; charset=utf-8'

        template = jinja_environment.get_template('templates/atom_feed.xml')
        self.response.out.write(template.render(template_values))


class QuoteHandler(webapp2.RequestHandler):
    def post(self, quoteid):
        user = users.get_current_user()
        modals.del_quote(long(quoteid), user)
        self.redirect('/')

    def get(self, quoteid):
        quote = modals.get_quote(long(quoteid))
        if quote is None:
            self.response.set_status(404, 'Not Found')
            return
        user = users.get_current_user()
        quotes = [quote]

        comments = modals.get_comments(quoteid)

        template_values = create_template_dict_single_quote(user, quotes, 'Quote', comments, nexturi=None, prevuri=None,
                                                            page=0)

        template = jinja_environment.get_template('templates/singlequote.html')
        self.response.out.write(template.render(template_values))


class MainHandler(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
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

        template_values = create_template_dict_main(
            user, quotes, 'Popular', quotesr, 'Recent', nexturi, prevuri, pager, nexturir, None
        )

        template = jinja_environment.get_template('templates/index.html')
        self.response.out.write(template.render(template_values))

    def post(self):
        user = users.get_current_user()
        title = self.request.get('title')
        text = self.request.get('quote').strip()
        if len(text) > 500:
            text = text[:500]
        if len(title) > 75:
            title = title[:75]
        uri = self.request.get('url').strip()
        parsed_uri = urlparse(uri)

        if uri and (not parsed_uri.scheme or not parsed_uri.netloc):
            template_values = {
                'loggedin': user,
                'title': title,
                'text': text,
                'uri': uri,
                'error_msg': 'The supplied link is not a valid absolute URI'
            }

            template = jinja_environment.get_template('templates/add_quote_error.html')
            self.response.out.write(template.render(template_values))

        else:
            if len(title) != 0 and title is not None:
                quote_id = modals.add_quote(title, user, text, url1=uri)
                if quote_id is not None:
                    modals.set_vote(long(quote_id), user, 1)
                    self.redirect('/')
                else:
                    template_values = {
                        'loggedin': user,
                        'title': title,
                        'text': text,
                        'uri': uri,
                        'error_msg': 'An error occured while adding this quote, please try again.'
                    }

                    template = jinja_environment.get_template('templates/add_quote_error.html')
                    self.response.out.write(template.render(template_values))
            else:
                template_values = {
                    'loggedin': user,
                    'title': title,
                    'text': text,
                    'uri': uri,
                    'error_msg': 'An error occured while adding this quote, please try again. you forgot to enter title.'
                }

                template = jinja_environment.get_template('templates/add_quote_error.html')
                self.response.out.write(template.render(template_values))


class UploadPicture(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        user = users.get_current_user()
        title = self.request.get('title')
        text = self.request.get('quote').strip()
        if len(text) > 500:
            text = text[:500]
        if len(title) > 75:
            title = title[:75]
        uri = self.request.get('url').strip()
        parsed_uri = urlparse(uri)

        if uri and (not parsed_uri.scheme or not parsed_uri.netloc):
            template_values = {
                'loggedin': user,
                'title': title,
                'text': text,
                'uri': uri,
                'error_msg': 'The supplied link is not a valid absolute URI'
            }

            template = jinja_environment.get_template('templates/add_quote_error.html')
            self.response.out.write(template.render(template_values))

        else:
            image = self.get_uploads('image')
            type = image[0].content_type

            if image and type.startswith('image/') and len(title) != 0:
                blob_info = image[0]
                image = blob_info.key()

                quote_id = modals.add_quote(title, user, text, url1=uri, image=image)
                if quote_id is not None:
                    modals.set_vote(long(quote_id), user, 1)
                    self.redirect('/')
                else:
                    template_values = {
                        'loggedin': user,
                        'title': title,
                        'text': text,
                        'uri': uri,
                        'error_msg': 'An error occured while adding this quote, please try again.'
                    }

                    template = jinja_environment.get_template('templates/add_quote_error.html')
                    self.response.out.write(template.render(template_values))
            else:
                blob_info = image[0]
                image = blob_info.key()
                blobstore.delete(image)
                self.redirect('/')


class TopHandler(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
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
        template_values = create_template_dict(user, quotes, section, nexturi, prevuri, page)

        template = jinja_environment.get_template('templates/top.html')
        self.response.out.write(template.render(template_values))


class SubmitHandler(webapp2.RequestHandler):
    def get(self):
        template_values = {
            'loggedin': users.get_current_user(),
            'greeting': get_greeting(),
        }
        template = jinja_environment.get_template('templates/submit.html')
        self.response.out.write(template.render(template_values))


class SearchHandler(webapp2.RequestHandler):
    def get(self):
        uri = urlparse(self.request.uri)
        query = 'null'
        if uri.query:
            query = parse_qs(uri.query)
            query = query['query'][0]

        if query is not 'null':
            user = users.get_current_user()
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

            template_values = create_template_dict(user, quotes, section, nexturi, prevuri, page)
            template = jinja_environment.get_template('templates/search.html')
            self.response.out.write(template.render(template_values))

        else:
            template_values = {
                'loggedin': users.get_current_user(),
                'greeting': get_greeting(),
            }
            template = jinja_environment.get_template('templates/search.html')
            self.response.out.write(template.render(template_values))


class CommentHandler(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()
        if None == user:
            self.response.set_status(403, 'Forbidden')
            return
        quoteid = self.request.get('quoteid')
        text = self.request.get('comment')

        modals.add_comment(user, quoteid, text)
        self.redirect('/post/' + quoteid)


class CommentDeleterHandler(webapp2.RequestHandler):
    def post(self, commentid):
        quoteid = self.request.get('quoteid')

        user = users.get_current_user()
        modals.del_comment(quoteid, commentid, user)
        self.redirect('/post/' + quoteid)


application = webapp2.WSGIApplication(
    [
        ('/', MainHandler),
        ('/vote/', VoteHandler),
        ('/post/(.*)', QuoteHandler),
        ('/top', TopHandler),
        ('/image_post', UploadPicture),
        ('/submit', SubmitHandler),
        ('/add_comment', CommentHandler),
        ('/del_comment/(.*)', CommentDeleterHandler),
        ('/search', SearchHandler),
        ('/feed/(recent|popular)/', FeedHandler),
    ], debug=True)


def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
