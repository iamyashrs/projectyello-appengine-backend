from protorpc import messages


class Post(messages.Message):
    id = messages.IntegerField(1)
    title = messages.StringField(2, required=True)
    quote = messages.StringField(3)
    image = messages.StringField(4)
    creator = messages.StringField(5)
    created = messages.StringField(6)
    url = messages.StringField(7)
    votesum = messages.IntegerField(8)
    comments = messages.IntegerField(9)
    creator_anonymous = messages.BooleanField(10)


class AddPost(messages.Message):
    title = messages.StringField(1, required=True)
    quote = messages.StringField(2)
    image = messages.BytesField(3)
    user = messages.StringField(4, required=True)
    url = messages.StringField(5)
    user_anonymous = messages.BooleanField(6, required=True)
    provider = messages.StringField(7, required=True)


class PostCollection(messages.Message):
    posts = messages.MessageField(Post, 1, repeated=True)
    limit = messages.IntegerField(2)


class Vote(messages.Message):
    vote = messages.IntegerField(1)


class Voter(messages.Message):
    count = messages.IntegerField(1)
    hasVoted = messages.BooleanField(2, default=False)
    hasAddedQuote = messages.BooleanField(3, default=False)


class Comment(messages.Message):
    id = messages.IntegerField(1)
    author = messages.StringField(2)
    text = messages.StringField(3)
    made_on = messages.StringField(4)
    author_anonymous = messages.BooleanField(5)


class AddComment(messages.Message):
    author = messages.StringField(1, required=True)
    text = messages.StringField(2, required=True)
    post_id = messages.IntegerField(3, required=True)
    author_anonymous = messages.BooleanField(4, required=True)
    provider = messages.StringField(5, required=True)


class Response(messages.Message):
    success = messages.BooleanField(1, required=True)
    # details = messages.StringField(2)


class CommentCollection(messages.Message):
    comments = messages.MessageField(Comment, 1, repeated=True)
    # limit = messages.IntegerField(2)


class Search(messages.Message):
    query = messages.StringField(1, required=True)
    limit = messages.IntegerField(2, required=True)
