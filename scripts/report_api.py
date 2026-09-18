"""Small shared HTTP and Markdown helpers for scanner reports."""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ReportError(Exception):
    """An unavailable or unverifiable report must not change the scanner result."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Credentials must remain with the configured server.
        return None


class Api:
    def __init__(self, base_url, token, header='Authorization'):
        self.base_url = http_url(base_url).rstrip('/')
        self.headers = {header: ('Bearer ' if header == 'Authorization' else '') + token}
        self.http = build_opener(NoRedirect())

    def request(self, path, method='GET', values=None):
        url, data = self.base_url + path, None
        if method == 'GET' and values:
            url += '?' + urlencode(values)
        elif values is not None:
            data = json.dumps(values).encode()
        request = Request(url, method=method, data=data,
                          headers={**self.headers, 'Content-Type': 'application/json'})
        try:
            with self.http.open(request, timeout=10) as response:
                return json.load(response)
        except HTTPError as error:
            raise ReportError(f'Report API returned HTTP {error.code}.') from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise ReportError('Report API is unavailable or returned invalid JSON.') from None


def http_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
            or parsed.password or re.search(r'[\x00-\x20\x7f]', value)):
        raise ReportError('Expected an HTTP(S) URL without credentials or whitespace.')
    return value


def markdown(value):
    return str(value).replace('\\', '\\\\').replace('`', '\\`').replace('|', '\\|').replace('\n', ' ')


def link(label, url):
    # Angle-bracket links preserve query strings and parentheses in dashboard URLs.
    target = quote(http_url(url), safe=":/?#[]@!$&'()+,;=%-._~")
    return f'[{label}](<{target}>)'


def publish_mr(api, project, iid, body, marker):
    author = api.request('/user')['id']
    path = f'/projects/{quote(str(project), safe="")}/merge_requests/{int(iid)}/notes'
    page = 1
    while True:
        notes = api.request(path, values={'per_page': 100, 'page': page})
        for note in notes:
            if note['author']['id'] == author and note['body'].startswith(marker + '\n'):
                if note['body'] != body:
                    api.request(f"{path}/{note['id']}", 'PUT', {'body': body})
                    return 'updated'
                return 'unchanged'
        if len(notes) < 100:
            break
        page += 1
    api.request(path, 'POST', {'body': body})
    return 'created'

