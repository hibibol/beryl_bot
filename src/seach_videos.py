import apiclient
from setting import YOUTUBE_API_KEY


def init_youtube():
    return apiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


YOUTUBE = init_youtube()


def search_videos(q: str):
    """
    YouTube Data APIを用いて動画をupload dateの順で検索した結果を返す
    引数
        q:検索word
    返り値
        items (検索リソース)
    """
    search_response = YOUTUBE.search().list(part="snippet", q=q, order="date", type="video").execute()
    return search_response["items"]
