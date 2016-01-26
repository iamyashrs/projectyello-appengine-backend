import datetime
import logging
import hashlib

from google.appengine.ext import db, ndb
from google.appengine.api import memcache, images
from google.appengine.api import search
from google.appengine.ext import blobstore
from webapp2_extras.appengine.auth.models import User

PAGE_SIZE = 18
PAGE_SIZE_RECENT = 17
DAY_SCALE = 4
COMMENTS_ON_PAGE = 30
_INDEX_SEARCH = 'search'


class Post(ndb.Model):
    @property
    def to_dict(self):
        items = {'id': self.key.id(), 'title': self.title, 'quote': self.quote, 'creator': self.creator.get().email,
                 'created': self.made_on.isoformat(), 'url': self.uri, 'votesum': self.votesum,
                 'comments': self.comments, 'creator_anonymous': self.creator_anonymous}
        # items['created']=self.made_on.strftime('%Y-%m-%dT%H:%M:%S')
        try:
            items['image'] = images.get_serving_url(self.image)
        except:
            pass
        return items

    title = ndb.StringProperty(required=True)
    quote = ndb.StringProperty()
    uri = ndb.StringProperty()
    rank = ndb.StringProperty()
    image = ndb.BlobKeyProperty()
    creation_order = ndb.StringProperty(default=" ")
    votesum = ndb.IntegerProperty(default=0)
    created = ndb.IntegerProperty(default=0)
    made_on = ndb.DateTimeProperty(auto_now_add=True)
    creator = ndb.KeyProperty(kind=User)
    creator_anonymous = ndb.BooleanProperty()
    comments = ndb.IntegerProperty(default=0)


class Vote(ndb.Model):
    vote = ndb.IntegerProperty(default=0)


class Voter(ndb.Model):
    count = ndb.IntegerProperty(default=0)
    hasVoted = ndb.BooleanProperty(default=False)
    hasAddedQuote = ndb.BooleanProperty(default=False)


class Comment(ndb.Model):
    @property
    def to_dict(self):
        items = {'id': self.key.id(), 'author': self.author.get().email, 'made_on': self.made_on.isoformat(),
                 'text': self.text, 'author_anonymous': self.author_anonymous}
        return items

    author = ndb.KeyProperty(kind=User)
    author_anonymous = ndb.BooleanProperty()
    text = ndb.StringProperty()
    made_on = ndb.DateTimeProperty(auto_now_add=True)


def _get_or_create_voter(user):
    voter = Voter.get_by_id(user.email)
    if voter is None:
        voter = Voter(id=user.email)
    return voter


def _unique_user(user):
    def txn():
        voter = _get_or_create_voter(user)
        voter.count += 1
        voter.hasAddedQuote = True
        voter.put()
        return voter.count

    count = ndb.transaction(txn)

    return hashlib.md5(user.email + "|" + str(count)).hexdigest()


def add_quote(title1, user_id, user_anon, provider, quote1=None, url1=None, image=None, _created=None):
    try:
        now = datetime.datetime.now()

        if isinstance(user_id, unicode):
            auth_id = '%s:%s' % (provider, user_id)
            user = User.get_by_auth_id(auth_id)
        else:
            user = user_id

        unique_user = _unique_user(user)
        if _created:
            created = _created
        else:
            created = (now - datetime.datetime(2008, 10, 1)).days

        q = Post(
                title=title1,
                quote=quote1,
                created=created,
                image=image,
                creator_anonymous=user_anon,
                creator=user.key,
                creation_order=now.isoformat()[:19] + "|" + unique_user,
                uri=url1
        )
        q.put()

        add_search_index(q.key.id(), title1, quote1, url1, image, user, user_anon)
        return q.key.id()

    except db.Error:
        return None


def add_comment(user, user_anon, quote_id, text, provider):
    try:
        if user is None:
            return

        if isinstance(user, unicode):
            auth_id = '%s:%s' % (provider, user)
            user = User.get_by_auth_id(auth_id)
        else:
            user = user

        quote = Post.get_by_id(long(quote_id))
        comment = Comment(
                parent=quote.key,
                author_anonymous=user_anon,
                author=user.key,
                text=text
        )
        quote.comments += 1

        quote.put()
        comment.put()
        memcache.set("comment|" + user.email + "|" + str(quote_id), comment.text)

    except db.Error:
        return None


def del_quote(quote_id, user):
    q = Post.get_by_id(quote_id)
    if q is not None and q.creator == user.key:
        comments = get_comments(quote_id)
        votes = get_vote(quote_id)

        for comment in comments:
            comment.key.delete()
        for vote in votes:
            vote.key.delete()

        if q.image is not None:
            blobstore.delete(q.image)

        q.key.delete()

        doc_index = search.Index(name=_INDEX_SEARCH)
        if doc_index.get(doc_id=str(q.key.id())):
            doc_index.delete(document_ids=str(q.key.id()))

        logging.debug('Deleting the post!: %s and all the comments!' % quote_id)


def del_comment(quote_id, comment_id, user):
    q = Post.get_by_id(long(quote_id))
    c = Comment.get_by_id(long(comment_id), parent=q.key)

    if c is not None and c.author == user.key:
        c.key.delete()
        q.comments -= 1
        q.put()


def get_quote(quote_id):
    return Post.get_by_id(quote_id)


def get_comments(quote_id):
    # assert limit > 0
    quote = Post.get_by_id(long(quote_id))
    comments = Comment.query(ancestor=quote.key).order(Comment.made_on)

    return comments


def get_vote(quote_id):
    quote = Post.get_by_id(long(quote_id))
    votes = Vote.query(ancestor=quote.key)

    return votes


def get_quotes_newest(offset=None):
    extra = None
    if offset is None:
        quotes = Post.gql('ORDER BY creation_order DESC').fetch(PAGE_SIZE_RECENT + 1)
    else:
        quotes = Post.gql("""WHERE creation_order <= :1 ORDER BY creation_order DESC""", offset).fetch(
                PAGE_SIZE_RECENT + 1)

    if len(quotes) > PAGE_SIZE_RECENT:
        extra = quotes[-1].creation_order
        quotes = quotes[:PAGE_SIZE_RECENT]
    return quotes, extra


def set_vote(quote_id, user_id, newvote, provider):
    if user_id is None:
        return

    if isinstance(user_id, unicode):
        auth_id = '%s:%s' % (provider, user_id)
        user = User.get_by_auth_id(auth_id)
    else:
        user = user_id

    email = user.email

    def txn():
        quote = Post.get_by_id(quote_id)
        vote = Vote.get_by_id(id=email, parent=quote.key)
        if vote is None:
            vote = Vote(id=email, parent=quote.key)
        if vote.vote == newvote:
            return
        quote.votesum = quote.votesum - vote.vote + newvote
        vote.vote = newvote

        quote.rank = "%020d|%s" % (
            long(quote.created * DAY_SCALE + quote.votesum),
            quote.creation_order
        )
        quote.put()
        vote.put()
        memcache.set("vote|" + email + "|" + str(quote_id), vote.vote)

    ndb.transaction(txn)


def get_quotes(page=0):
    assert page >= 0
    assert page < 20
    extra = None
    quotes = Post.gql('ORDER BY rank DESC').fetch(limit=PAGE_SIZE + 1, offset=page * PAGE_SIZE)
    if len(quotes) > PAGE_SIZE:
        if page < 19:
            extra = quotes[-1]
        quotes = quotes[:PAGE_SIZE]
    return quotes, extra


def get_recent(limit=20):
    assert limit > 0
    quotes = Post.gql('ORDER BY creation_order DESC').fetch(limit)
    return quotes


def get_popular(limit=20):
    assert limit > 0
    quotes = Post.gql('ORDER BY rank DESC').fetch(limit)
    return quotes


def get_top(limit=20):
    assert limit > 0
    quotes = Post.gql('ORDER BY votesum DESC').fetch(limit)
    return quotes


def get_search(query, limit=20):
    assert limit > 0

    expr_list = [search.SortExpression(
            expression='author', default_value='',
            direction=search.SortExpression.DESCENDING)]

    sort_opts = search.SortOptions(expressions=expr_list)
    query_options = search.QueryOptions(limit=limit, sort_options=sort_opts)
    query_obj = search.Query(query_string=query, options=query_options)

    results_posts = search.Index(name=_INDEX_SEARCH).search(query=query_obj)
    results = []
    for result in results_posts:
        a = Post.get_by_id(long(result.doc_id))
        results.append(a)

    return results


def get_quotes_top(page=0):
    assert page >= 0
    assert page < 20
    extra = None
    quotes = Post.gql('ORDER BY votesum DESC').fetch(limit=PAGE_SIZE + 1, offset=page * PAGE_SIZE)
    if len(quotes) > PAGE_SIZE:
        if page < 19:
            extra = quotes[-1]
        quotes = quotes[:PAGE_SIZE]
    return quotes, extra


def voted(quote, user):
    val = 0
    if user:
        memcachekey = "vote|" + user.email + "|" + str(quote.key.id())
        val = memcache.get(memcachekey)
        if val is not None:
            return val
        vote = Vote.get_by_id(id=user.email, parent=quote.key)
        if vote is not None:
            val = vote.vote
            memcache.set(memcachekey, val)
    return val


def CreatePostDoc(post_id, author, title, quote, link, image, author_anon):
    if author:
        nickname = author
    else:
        nickname = 'anonymous'
    if author_anon:
        isAnon = 'true'
    else:
        isAnon = 'false'

    return search.Document(doc_id=post_id,
                           fields=[search.TextField(name='author', value=nickname),
                                   search.TextField(name='title', value=title),
                                   search.TextField(name='quote', value=quote),
                                   search.TextField(name='link', value=link),
                                   search.DateField(name='made_on', value=datetime.datetime.now()),
                                   search.TextField(name='image', value=image),
                                   search.TextField(name='author_anonymous', value=isAnon)])


def add_search_index(post_id, title, quote, link, image, user, user_anon):
    doc_index = search.Index(name=_INDEX_SEARCH)

    if doc_index.get(doc_id=str(post_id)):
        doc_index.delete(document_ids=str(post_id))

    search.Index(name=_INDEX_SEARCH).put(
            CreatePostDoc(str(post_id), user.email, title, quote, link, str(image), user_anon))


def get_search_results(query, page=0):
    assert page >= 0
    assert page < 20
    extra = None

    expr_list = [search.SortExpression(
            expression='author', default_value='',
            direction=search.SortExpression.DESCENDING)]

    sort_opts = search.SortOptions(expressions=expr_list)
    query_options = search.QueryOptions(limit=30, sort_options=sort_opts)
    query_obj = search.Query(query_string=query, options=query_options)

    results_posts = search.Index(name=_INDEX_SEARCH).search(query=query_obj)
    results = []
    for result in results_posts:
        a = Post.get_by_id(long(result.doc_id))
        results.append(a)

    if len(results) > PAGE_SIZE:
        if page < 19:
            extra = results[-1]
        quotes = results[:PAGE_SIZE]

    return results, extra
