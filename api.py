import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from messages import PostCollection
from messages import CommentCollection
from messages import AddComment
from messages import AddPost
from messages import Response
from messages import Search
import services
import modals
import handlers

package = 'API'


@endpoints.api(name='projectyello', version='v1')
class ProjectYelloApi(remote.Service):
    POSTS_LIMIT_RESOURCE = endpoints.ResourceContainer(message_types.VoidMessage,
                                                       limit=messages.IntegerField(1, variant=messages.Variant.INT32))

    COMMENTS_LIMIT_RESOURCE = endpoints.ResourceContainer(message_types.VoidMessage,
                                                          post_id=messages.StringField(2,
                                                                                       variant=messages.Variant.STRING))

    @endpoints.method(POSTS_LIMIT_RESOURCE, PostCollection, path='posts/recent', http_method='GET', name='posts.Recent')
    def recent_posts(self, request):
        if hasattr(request, 'limit'):
            post_list = modals.get_recent(request.limit)
        else:
            post_list = modals.get_recent()

        posts = services.ApiUtils.serialize_posts(post_list)
        return PostCollection(posts=posts, limit=request.limit)

    @endpoints.method(POSTS_LIMIT_RESOURCE, PostCollection, path='posts/popular', http_method='GET',
                      name='posts.Popular')
    def popular_posts(self, request):
        if hasattr(request, 'limit'):
            post_list = modals.get_popular(request.limit)
        else:
            post_list = modals.get_popular()

        posts = services.ApiUtils.serialize_posts(post_list)
        return PostCollection(posts=posts, limit=request.limit)

    @endpoints.method(POSTS_LIMIT_RESOURCE, PostCollection, path='posts/top', http_method='GET', name='posts.Top')
    def top_posts(self, request):
        if hasattr(request, 'limit'):
            post_list = modals.get_top(request.limit)
        else:
            post_list = modals.get_top()

        posts = services.ApiUtils.serialize_posts(post_list)
        return PostCollection(posts=posts, limit=request.limit)

    @endpoints.method(AddPost, Response, path='posts/add', http_method='POST', name='posts.AddPost')
    def add_post(self, request):
        user = request.user
        # user = endpoints.get_current_user()
        # user = handlers.BaseRequestHandler.current_user()
        if user is None:
            raise endpoints.UnauthorizedException('Invalid token.')
        resp = services.ApiUtils.add_post(user, request.title, request.quote, request.user_anonymous, request.provider,
                                          request.url, request.image)
        return Response(success=resp)

    @endpoints.method(Search, PostCollection, path='posts/search_posts', http_method='GET', name='posts.Search')
    def search_posts(self, request):
        if hasattr(request, 'query'):
            post_list = modals.get_search(request.query, request.limit)
            posts = services.ApiUtils.serialize_posts(post_list)
            return PostCollection(posts=posts, limit=request.limit)

    @endpoints.method(COMMENTS_LIMIT_RESOURCE, CommentCollection, path='posts/comments', http_method='GET',
                      name='posts.Comments')
    def comments(self, request):
        if hasattr(request, 'post_id'):
            comment_list = modals.get_comments(request.post_id)
        else:
            return
        comments = services.ApiUtils.serialize_comments(comment_list)
        return CommentCollection(comments=comments)

    @endpoints.method(AddComment, Response, path='posts/comments', http_method='POST', name='posts.AddComment')
    def add_comment(self, request):
        author = request.author
        # user = endpoints.get_current_user()
        # user = handlers.BaseRequestHandler.current_user()
        resp = services.ApiUtils.add_comment(user=author, quoteid=request.post_id, text=request.text,
                                             provider=request.provider, user_anon=request.author_anonymous)
        return Response(success=resp)


application = endpoints.api_server([ProjectYelloApi])
