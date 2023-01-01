import requests
from bs4 import BeautifulSoup
import random
import re
import base64
import json


# константы

class Error:
    UNKNOWN_ERROR = -1
    SEARCH_ERROR = 0
    PROXY_ERROR = 1
    GET_ITEM_ERROR = 2
    GET_EPISODES_ERROR = 3
    GET_STREAM_ERROR = 4
    GET_MOVIE_ERROR = 5
    PROCESS_STREAM_ERROR = 6
    GET_POPULAR_ERROR = 7
    GET_QUICK_CONTENT_ERROR = 8

class LogLevel:
    DEBUG = 0
    INFO = 1

    TO_STRING = {
        DEBUG: "[DEBUG]",
        INFO: "[INFO]",
    }

    CURRENT = DEBUG

class ItemType:
    SERIES = 0
    MOVIE = 1

class StreamType:
    MP4 = 0
    M3U8 = 1

# полный адрес хоста (обязательно / в конце)
HOST = "https://hdrezka.me/"

SEARCH_QUERY = "search/?do=search&subaction=search&q={}"
GET_CDN_SERIES = "ajax/get_cdn_series/"
GET_QUICK_CONTENT = "engine/ajax/quick_content.php"
USE_PROXY = False
PROXIES = [
    "http://hylmtsyx:2x5hcj64w5vy@154.194.10.231:6244",
]
REQUEST_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36",
}
RAW_RESPONSES = False
STREAM_TYPE = StreamType.MP4


# классы

class SearchItem:
    def __init__(self, title, coverUrl, summary, url, id):
        self.title = title
        self.coverUrl = coverUrl
        self.summary = summary
        self.url = url
        self.id = id

    def __repr__(self):
        return f"{{ title: {self.title}, url: {self.url}, coverUrl: {self.coverUrl}, summary: {self.summary} }}"

    def getItem(self):
        return getItem(self.url)

    def getQuickContent(self):
        return getQuickContent(self.id)

class Translator:
    def __init__(self, title, id, additional):
        self.title = title
        self.id = id
        self.additional = additional

class Item:
    def __init__(self, title, coverUrl, description, url, translators, defaults, type, originalTitle=''):
        self.title = title
        self.originalTitle = originalTitle
        self.coverUrl = coverUrl
        self.description = description
        self.url = url
        self.translators = translators
        self.type = type
        self.defaults = defaults

    def __repr__(self):
        return f"{{ title: {self.title}, originalTitle: {self.originalTitle}, coverUrl: {self.coverUrl}, description: {self.description}, url: {self.url}, translators: {self.translators}, type: {self.type}, defaults: {self.defaults} }}"


# утилс

def printToLog(logLevel, *args, **kwargs):
    if logLevel < LogLevel.CURRENT:
        return

    print(LogLevel.TO_STRING[logLevel], *args, **kwargs)

def throwError(errorType, additionalInfo=''):
    if errorType == Error.SEARCH_ERROR:
        raise Exception(f"Проблема с поиском [{additionalInfo}]")
    if errorType == Error.PROXY_ERROR:
        raise Exception(f"Проблема с прокси [{additionalInfo}]")
    if errorType == Error.GET_ITEM_ERROR:
        raise Exception(f"Проблема с получением Item [{additionalInfo}]")
    if errorType == Error.GET_EPISODES_ERROR:
        raise Exception(f"Проблема с получением эпизодов [{additionalInfo}]")
    if errorType == Error.GET_STREAM_ERROR:
        raise Exception(f"Проблема с получением стрима (get_stream) [{additionalInfo}]")
    if errorType == Error.GET_MOVIE_ERROR:
        raise Exception(f"Проблема с получением стрима (get_movie) [{additionalInfo}]")
    if errorType == Error.PROCESS_STREAM_ERROR:
        raise Exception(f"Проблема с получением стрима [{additionalInfo}]")
    if errorType == Error.GET_POPULAR_ERROR:
        raise Exception(f"Проблема получения популярного сейчас [{additionalInfo}]")
    if errorType == Error.GET_QUICK_CONTENT_ERROR:
        raise Exception(f"Проблема получения быстрого контента [{additionalInfo}]")
    raise Exception(f"Неизвестная ошибка [{additionalInfo}]")

def getRandomProxy():
    if not USE_PROXY:
        throwError(Error.PROXY_ERROR, "USE_PROXY равен False")
    if not PROXIES:
        throwError(Error.PROXY_ERROR, "Пустой список прокси")
    randomProxy = random.choice(PROXIES)
    return { 'http': randomProxy, 'https': randomProxy }

def makeRequest(**kwargs):
    if USE_PROXY:
        kwargs["proxies"] = getRandomProxy()
    kwargs["headers"] = REQUEST_HEADERS
    printToLog(LogLevel.DEBUG, "Выполняем запрос к {}\nПрокси? {}".format(
        kwargs["url"],
        kwargs["proxies"] if USE_PROXY else "Нет",
    ))
    return requests.request(**kwargs)

# скопированная функция хз откуда
def unhashUrl(hashed_token):
    salts = ["$$!!@$$@^!@#$$@",
            "@@@@@!##!^^^",
            "####^!!##!@@",
            "^^^!@##!!##",
            "$$#!!@#!@##"]
    b1 = lambda s: base64.b64encode(s.encode()).decode()
    b2 = lambda s: base64.b64decode(s.encode()).decode()
    str_to_decode = hashed_token[2:]
    for salt in salts:
        str_to_decode = str_to_decode.replace(f"//_//{b1(salt)}", "")
    return b2(str_to_decode)


# основные функции

def makeSearch(searchQuery):
    printToLog(LogLevel.INFO, f"Выполняем поиск: {searchQuery}")
    r = makeRequest(
        method="GET",
        url=HOST+SEARCH_QUERY.format(searchQuery)
    )
    if r.status_code != 200:
        throwError(Error.SEARCH_ERROR, f"запрос: {searchQuery}, статус запроса: {r.status_code}")
    searchItems = []

    soup = BeautifulSoup(r.text, "html.parser")
    for inlineItem in soup.find_all("div", class_="b-content__inline_item"):
        itemLink = inlineItem.find("div", class_="b-content__inline_item-link")
        itemCover = inlineItem.find("div", class_="b-content__inline_item-cover")
        searchItems.append(SearchItem(
            url=itemLink.find("a")["href"],
            title=itemLink.find("a").get_text(),
            summary=itemLink.find("div").get_text(),
            coverUrl=itemCover.find("img")["src"],
            id=inlineItem["data-id"]
        ))

    return searchItems

def processStreamResponse(r):
    r = r.json()
    if r["success"] != True:
        throwError(Error.PROCESS_STREAM_ERROR, f"Ответ на запрос: {r}")

    # декодим url
    r["url"] = unhashUrl(r["url"])

    # возвращаем оригинальный ответ с нормальным url
    if RAW_RESPONSES:
        return json.dumps(r)

    streams = {}
    for streamUrlOr in r["url"].split(","):
        reQuality = re.match(r"\[([^\]]+)\]", streamUrlOr)
        streamQuality = reQuality[1]
        streamUrl = streamUrlOr[reQuality.span()[1]:].split(" or ")[1 if STREAM_TYPE is StreamType.MP4 else 0]
        streams[streamQuality] = streamUrl

    subtitles = {}
    if r["subtitle"]:
        for subtitle in r["subtitle"].split(","):
            reLanguage = re.match(r"\[([^\]]+)\]", subtitle)
            subtitleLanguage = reLanguage[1]
            subtitleUrl = subtitle[reLanguage.span()[1]:]
            subtitles[subtitleLanguage] = subtitleUrl

    return streams, subtitles

def getStream(itemId, translatorId, seasonId, episodeId):
    printToLog(LogLevel.INFO, f"Получаем стрим: {itemId}, {translatorId}, {seasonId}, {episodeId}")
    r = makeRequest(
        method="POST",
        url=HOST+GET_CDN_SERIES,
        data={
            "id": itemId,
            "translator_id": translatorId,
            "season": seasonId,
            "episode": episodeId,
            "action": "get_stream",
        }
    )
    if r.status_code != 200:
        throwError(
            Error.GET_STREAM_ERROR,
            f"item ID: {itemId}, translator ID: {translatorId}, season ID: {seasonId}, episode ID: {episodeId}, статус запроса: {r.status_code}"
        )

    return processStreamResponse(r)

def getMovie(itemId, translatorId, isCamrip=0, isAds=0, isDirector=0):
    printToLog(LogLevel.INFO, f"Получаем муви: {itemId}, {translatorId}, {isCamrip}, {isAds}, {isDirector}")
    r = makeRequest(
        method="POST",
        url=HOST+GET_CDN_SERIES,
        data={
            "id": itemId,
            "translator_id": translatorId,
            "is_camrip": isCamrip,
            "is_ads": isAds,
            "is_director": isDirector,
            "action": "get_movie",
        }
    )
    if r.status_code != 200:
        throwError(Error.GET_MOVIE_ERROR, f"item ID: {itemId}, translator ID: {translatorId}, is camrip: {isCamrip}, is ads: {isAds}, is director: {isDirector}, статус запроса: {r.status_code}")

    return processStreamResponse(r)

def getEpisodes(itemId, translatorId):
    printToLog(LogLevel.INFO, f"Получаем эпизоды: {itemId}, {translatorId}")
    r = makeRequest(
        method="POST",
        url=HOST+GET_CDN_SERIES,
        data={
            "id": itemId,
            "translator_id": translatorId,
            "action": "get_episodes",
        }
    )
    if r.status_code != 200:
        throwError(Error.GET_EPISODES_ERROR, f"item ID: {itemId}, translator ID: {translatorId}, статус запроса: {r.status_code}")

    if RAW_RESPONSES:
        return r.text

    r = r.json()
    if r["success"] != True:
        throwError(Error.GET_EPISODES_ERROR, f"Ответ на запрос: {r}")

    soup = BeautifulSoup(r["seasons"], "html.parser")
    seasons = []
    for seasonItem in soup.find_all("li"):
        seasons.append({
            "title": seasonItem.get_text(),
            "id": seasonItem["data-tab_id"],
        })

    soup = BeautifulSoup(r["episodes"], "html.parser")
    episodes = []
    for episodesListItem in soup.find_all("ul"):
        episodesList = []
        for episodeItem in episodesListItem.find_all("li"):
            episodesList.append({
                "title": episodeItem.get_text(),
                "id": episodeItem["data-episode_id"],
            })
        episodes.append(episodesList)

    return seasons, episodes

def getPopular():
    printToLog(LogLevel.INFO, f"Получаем популярное сейчас")
    r = makeRequest(
        method="GET",
        url=HOST
    )
    if r.status_code != 200:
        throwError(Error.GET_POPULAR_ERROR, f"Статус запроса: {r.status_code}")

    soup = BeautifulSoup(r.text, "html.parser")
    popularItems = []
    for inlineItem in soup.find("div", class_="b-newest_slider").find_all("div", class_="b-content__inline_item"):
        itemLink = inlineItem.find("div", class_="b-content__inline_item-link")
        itemCover = inlineItem.find("div", class_="b-content__inline_item-cover")
        popularItems.append(SearchItem(
            title=itemLink.find("a").get_text(),
            url=HOST[:-1] + itemLink.find("a")["href"],
            summary=itemLink.find("div").get_text(),
            coverUrl=itemCover.find("img")["src"],
            id=inlineItem["data-id"]
        ))
    return popularItems

def getItem(url):
    printToLog(LogLevel.INFO, f"Получаем Item: {url}")
    r = makeRequest(
        method="GET",
        url=url
    )
    if r.status_code != 200:
        throwError(Error.GET_ITEM_ERROR, f"URL запроса: {url}, статус запроса: {r.status_code}")

    soup = BeautifulSoup(r.text, "html.parser")


    # получаем дефолтные значения
    reSearch = re.search(r"sof.tv.initCDNSeriesEvents\((\d+), (\d+), (\d+), (\d+),", r.text)
    if reSearch:
        type = ItemType.SERIES
        defaults = tuple(reSearch[i] for i in range(1, 5))
    else:
        reSearch = re.search(r"sof.tv.initCDNMoviesEvents\((\d+), (\d+),", r.text)
        if reSearch:
            type = ItemType.MOVIE
            defaults = tuple(reSearch[i] for i in range(1, 3))
        else:
            throwError(Error.GET_ITEM_ERROR, "Не смогли получить defaults")
    printToLog(LogLevel.DEBUG, f"Получили defaults: {defaults}")


    # получаем переводы
    translators = []
    translatorsList = soup.find("ul", class_="b-translators__list")
    if translatorsList:
        for translatorItem in translatorsList.find_all("li"):
            try:
                additional = translatorItem["data-camrip"], translatorItem["data-ads"], translatorItem["data-director"]
            except KeyError:
                additional = ()
            translators.append(Translator(
                title=translatorItem["title"],
                id=translatorItem["data-translator_id"],
                additional=additional
            ))


    # получаем ориг тайтл (может не быть)
    origTitle = soup.find("div", class_="b-post__origtitle")

    item = Item(
        title=soup.find("div", class_="b-post__title").find("h1").get_text(),
        originalTitle=origTitle.get_text() if origTitle else '',
        description=soup.find("div", class_="b-post__description").find("div", class_="b-post__description_text").get_text(),
        translators=translators,
        coverUrl=soup.find("div", class_="b-sidecover").find("img")["src"],
        url=url,
        type=type,
        defaults=defaults
    )

    return item

def getQuickContent(itemId):
    printToLog(LogLevel.DEBUG, f"Получаем быстрый контент: {itemId}")
    r = makeRequest(
        method="POST",
        url=HOST+GET_QUICK_CONTENT,
        data={
            "id": itemId,
            "is_touch": 1
        }
    )
    if r.status_code != 200:
        throwError(Error.GET_QUICK_CONTENT_ERROR, f"Статус запроса: {r.status_code}")

    soup = BeautifulSoup(r.text, "html.parser")

    quickContent = {
        "description": soup.find("div", class_="b-content__bubble_text").get_text().strip(),
        "rezkaRating": soup.find("div", class_="b-content__bubble_rating").find("b").get_text()
    }

    imdbRating = soup.find("span", class_="imdb")
    if imdbRating:
        quickContent.update({
            "imdbRating": imdbRating.find("b").get_text()
        })

    kpRating = soup.find("span", class_="kp")
    if kpRating:
        quickContent.update({
            "kpRating": kpRating.find("b").get_text()
        })

    return quickContent
