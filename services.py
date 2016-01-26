import modals
from urlparse import urlparse


class ApiUtils(object):
    """Utility API functions."""

    @staticmethod
    def serialize_posts(posts):
        items = []
        for post in posts:
            items.append(post.to_dict)
        return items

    @staticmethod
    def serialize_comments(comments):
        items = []
        for comment in comments:
            items.append(comment.to_dict)
        return items

    @staticmethod
    def add_post(user, title, quote, user_anonymous, provider, url, image):
        if quote is not None:
            if len(quote) > 500:
                quote = quote[:500]
        if title is not None:
            if len(title) > 75:
                title = title[:75]
        if url is not None:
            uri = url.strip()
            parsed_uri = urlparse(uri)
            if uri and (not parsed_uri.scheme or not parsed_uri.netloc):
                return False
            else:
                if len(title) != 0 and title is not None:
                    quote_id = modals.add_quote(title1=title, user_id=user, user_anon=user_anonymous, provider=provider,
                                                quote1=quote, url1=url)
                    if quote_id is not None:
                        modals.set_vote(long(quote_id), user, 1, provider=provider)
                        return True
                    else:
                        return False
                else:
                    return False
        else:
            if len(title) != 0 and title is not None:
                quote_id = modals.add_quote(title1=title, user_id=user, provider=provider, quote1=quote, url1=url,
                                            user_anon=user_anonymous)
                if quote_id is not None:
                    modals.set_vote(long(quote_id), user, 1, provider=provider)
                    return True
                else:
                    return False
            else:
                return False

    @staticmethod
    def add_comment(user, quoteid, text, provider, user_anon):
        modals.add_comment(user=user, user_anon=user_anon, quote_id=quoteid, text=text, provider=provider)
        return True
