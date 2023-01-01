from urllib.parse import parse_qsl, urlencode, unquote_plus


def parsePluginParams(params):
    return dict(parse_qsl(params[1:]))

def encodePluginParams(params):
    return urlencode(params)

def buildPluginUrl(url, params):
    return url + '?' + encodePluginParams(params)