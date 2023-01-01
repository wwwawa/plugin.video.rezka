import sys

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

import api
import utils
import constants


__url__ = sys.argv[0]
__handle__ = int(sys.argv[1])
__params__ = sys.argv[2]
__addon__ = xbmcaddon.Addon()
__icon__ = __addon__.getAddonInfo('icon')


def _paintRating(rating):
    rating = float(rating)
    if 0 <= rating < 5:
        ratingColor = 'red'
    elif 5 <= rating < 7:
        ratingColor = 'yellow'
    else:
        ratingColor = 'green'
    return '[COLOR={}][{}][/COLOR]'.format(ratingColor, rating)


def _listSearchItems(searchItems):
    for searchItem in searchItems:
        itemContent = searchItem.getQuickContent()
        itemTitle = '{} {} [COLOR=55FFFFFF]({})[/COLOR]'.format(searchItem.title, _paintRating(itemContent['rezkaRating']), searchItem.summary)
        itemDescription = itemContent['description']
        if 'imdbRating' in itemContent:
            itemDescription = 'IMDb: {}\n'.format(_paintRating(itemContent['imdbRating'])) + itemDescription
        if 'kpRating' in itemContent:
            itemDescription = 'Кинопоиск: {}\n'.format(_paintRating(itemContent['kpRating'])) + itemDescription
        item = xbmcgui.ListItem(
            itemTitle
        )
        item.setInfo(
            type='video',
            infoLabels={
                'title': itemTitle,
                'plot': itemDescription
            }
        )
        item.setArt({
            'thumb': searchItem.coverUrl
        })
        xbmcplugin.addDirectoryItem(
            __handle__,
            utils.buildPluginUrl(__url__, {'mode': 'show', 'url': searchItem.url}),
            item,
            True
        )


def _selectQuality(params):
    if int(params['type']) == api.ItemType.SERIES:
        streams, subtitles = api.getStream(params['id'], params['translator'], params['season'], params['episode'])
    else:
        streams, subtitles = api.getMovie(params['id'], params['translator'], params.get('camrip', 0), params.get('ads', 0), params.get('director', 0))

    for streamQuality, streamUrl in reversed(streams.items()):
        item = xbmcgui.ListItem('{} - [COLOR=FFFFAA00]{}[/COLOR]'.format(params['title'], streamQuality))
        item.setInfo(
            type='video',
            infoLabels={
                'title': params['title']
            }
        )
        item.setProperty('IsPlayable', 'true')
        if subtitles:
            item.setSubtitles(tuple(subtitles.values()))
        item.setArt({
            'thumb': params['cover']
        })
        xbmcplugin.addDirectoryItem(
            __handle__,
            utils.buildPluginUrl(__url__, {'mode': 'play', 'url': streamUrl}),
            item,
            False
        )


def menu(params):
    item = xbmcgui.ListItem('[COLOR=FF00FF00]Поиск[/COLOR]')
    item.setArt({
        'thumb': __icon__
    })
    xbmcplugin.addDirectoryItem(
        __handle__,
        utils.buildPluginUrl(__url__, {'mode': 'search'}),
        item,
        True
    )

    item = xbmcgui.ListItem('[COLOR=FF00FF00]История просмотров[/COLOR]')
    item.setArt({
        'thumb': __icon__
    })
    xbmcplugin.addDirectoryItem(
        __handle__,
        utils.buildPluginUrl(__url__, {'mode': 'history'}),
        item,
        True
    )

    item = xbmcgui.ListItem('[COLOR=FF00FF00]Популярное[/COLOR]')
    item.setArt({
        'thumb': __icon__
    })
    xbmcplugin.addDirectoryItem(
        __handle__,
        utils.buildPluginUrl(__url__, {'mode': 'popular'}),
        item,
        True
    )

    xbmcplugin.setContent(__handle__, 'movies')
    xbmcplugin.endOfDirectory(__handle__)


def search(params):
    searchQuery = ''

    keyboard = xbmc.Keyboard()
    keyboard.setDefault(searchQuery)
    keyboard.setHeading('Поиск')
    keyboard.doModal()

    if keyboard.isConfirmed():
        searchQuery = keyboard.getText()

    if not searchQuery:
        return menu(params)

    searchItems = api.makeSearch(searchQuery)
    _listSearchItems(searchItems)
    xbmcplugin.setContent(__handle__, 'movies')
    xbmcplugin.endOfDirectory(__handle__, True)


def popular(params):
    popularItems = api.getPopular()
    _listSearchItems(popularItems)
    xbmcplugin.setContent(__handle__, 'movies')
    xbmcplugin.endOfDirectory(__handle__, True)


def show(params):
    url = params.get('url')
    item = api.getItem(url)

    params = {'url': item.url, 'type': item.type, 'id': item.defaults[0], 'translator': item.defaults[1], 'cover': item.coverUrl}

    if item.translators:
        dialog = xbmcgui.Dialog()
        translatorIndex = dialog.select('Выбрать озвучку', tuple(translator.title for translator in item.translators))
        translator = item.translators[translatorIndex]
        params.update({'translator': translator.id})
        if translator.additional:
            params.update(zip(('camrip', 'ads', 'director'), translator.additional))

    if item.type == api.ItemType.SERIES:
        params.update({'mode': 'play_episode'})

        for season, episodes in zip(*api.getEpisodes(params['id'], params['translator'])):
            for episode in episodes:
                itemTitle = '{} ({})'.format(episode['title'], season['title'])
                params.update({'season': season['id'], 'episode': episode['id'], 'title': itemTitle})
                item = xbmcgui.ListItem(itemTitle)
                item.setArt({
                    'thumb': params['cover']
                })
                xbmcplugin.addDirectoryItem(
                    __handle__,
                    utils.buildPluginUrl(__url__, params),
                    item,
                    True
                )

    else:
        params.update({'title': item.title})
        _selectQuality(params)

    xbmcplugin.setContent(__handle__, 'episodes')
    xbmcplugin.endOfDirectory(__handle__)


def play_episode(params):
    _selectQuality(params)
    xbmcplugin.setContent(__handle__, 'episodes')
    xbmcplugin.endOfDirectory(__handle__)


def play(params):
    streamUrl = params['url']
    item = xbmcgui.ListItem(path=streamUrl)
    xbmcplugin.setResolvedUrl(__handle__, True, item)


def main():
    params = utils.parsePluginParams(__params__)
    mode = params.get('mode')

    if mode is not None:
        globals()[mode](params)
    else:
        menu(params)


if __name__ == "__main__":
    main()
    # searchResult = r.makeSearch("люцифер")
    # item = searchResult[0].getItem()
    # print(r.getStream(*item.defaults))
    # print(r.getPopular())
    # print(r.makeSearch("люцифер"))
    # print(r.getItem("https://rezka.ag/films/thriller/48741-sera-2020.html"))
