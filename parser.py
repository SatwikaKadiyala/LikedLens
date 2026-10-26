"""Offline parser for Instagram liked-content exports and user-supplied metadata.
No Instagram authentication, scraping, or remote content fetching.
"""
import csv
import io
import json
import re
from pathlib import PurePosixPath
from urllib.parse import urlparse
from zipfile import ZipFile, BadZipFile

URL_PATTERN = re.compile(r'https?://(?:www\.)?instagram\.com/(?:p|reel|reels|tv)/[A-Za-z0-9_-]+', re.I)
ALLOWED = {'instagram.com', 'www.instagram.com'}
MAX_ENTRY = 25 * 1024 * 1024
MAX_ARCHIVE = 150 * 1024 * 1024
MAX_ITEMS = 100_000


def clean_url(url):
    if not isinstance(url, str):
        return ''
    match = URL_PATTERN.search(url)
    if not match:
        return ''
    parsed = urlparse(match.group(0))
    if parsed.hostname not in ALLOWED:
        return ''
    parts = parsed.path.strip('/').split('/')
    kind = 'reel' if parts[0].lower() in {'reel', 'reels'} else 'post'
    return f'https://www.instagram.com/{"reel" if kind == "reel" else "p"}/{parts[1]}/'


def normalize(row):
    url = clean_url(row.get('url') or row.get('href') or row.get('link') or '')
    if not url:
        return None
    typ = str(row.get('type', '')).lower()
    inferred = 'reel' if '/reel/' in url else 'post'
    typ = typ if typ in {'reel', 'post'} else inferred
    caption = row.get('caption') or row.get('description') or row.get('title') or ''
    tags = row.get('hashtags') or ''
    if isinstance(tags, list):
        tags = ' '.join(str(x) for x in tags)
    return {
        'url': url, 'type': typ,
        'caption': str(caption), 'hashtags': str(tags),
        'liked_at': str(row.get('liked_at') or row.get('timestamp') or ''),
        'media_file': str(row.get('media_file') or ''),
    }


def _from_json(data):
    """Supports common Meta activity shape and normalized JSON list; no guessing media access."""
    if isinstance(data, list):
        for obj in data:
            if isinstance(obj, dict):
                if 'string_list_data' in obj:
                    values = obj.get('string_list_data') or []
                    for item in values:
                        if isinstance(item, dict):
                            yield {'url': item.get('href', ''),
                                   'liked_at': item.get('timestamp', ''),
                                   'caption': ''}  # Meta title is often an account name, not the post caption
                elif obj.get('url') or obj.get('href') or obj.get('link'):
                    yield obj
    elif isinstance(data, dict):
        if data.get('url') or data.get('href'):
            yield data
        for key, value in data.items():
            if isinstance(value, (list, dict)) and (key.startswith('likes') or key in {'items', 'posts', 'reels', 'media_likes', 'data'}):
                yield from _from_json(value)


def _from_html(source):
    """Fallback for Meta HTML exports: extracts liked content links only; no caption inference."""
    for match in URL_PATTERN.finditer(source):
        yield {'url': match.group(0)}


def _from_csv(raw):
    decoded = raw.decode('utf-8-sig')
    yield from csv.DictReader(io.StringIO(decoded))


def _parse_file(name, raw):
    lower = name.lower()
    if lower.endswith('.json'):
        yield from _from_json(json.loads(raw.decode('utf-8-sig')))
    elif lower.endswith('.csv'):
        yield from _from_csv(raw)
    elif lower.endswith('.html') or lower.endswith('.htm'):
        yield from _from_html(raw.decode('utf-8', errors='replace'))


def parse_upload(filename, raw):
    if len(raw) > MAX_ARCHIVE:
        raise ValueError('Upload exceeds the 150 MB limit.')
    sources = []
    if filename.lower().endswith('.zip'):
        try:
            with ZipFile(io.BytesIO(raw)) as archive:
                files = [x for x in archive.infolist() if not x.is_dir() and
                         x.filename.lower().endswith(('.json', '.html', '.htm', '.csv')) and
                         ('liked' in PurePosixPath(x.filename).name.lower() or 'likes' in x.filename.lower())]
                if not files:
                    raise ValueError('No liked-content JSON/HTML/CSV file found in archive. Upload a liked_posts file or custom CSV.')
                if sum(x.file_size for x in files) > MAX_ARCHIVE:
                    raise ValueError('Uncompressed liked-data files exceed size limit.')
                for member in files:
                    if member.file_size > MAX_ENTRY:
                        raise ValueError(f'Export entry too large: {member.filename}')
                    sources.append((member.filename, archive.read(member)))
        except BadZipFile as exc:
            raise ValueError('Invalid ZIP file.') from exc
    elif filename.lower().endswith(('.json', '.csv', '.html', '.htm')):
        if len(raw) > MAX_ENTRY:
            raise ValueError('Individual input file exceeds the 25 MB limit.')
        sources = [(filename, raw)]
    else:
        raise ValueError('Upload a ZIP, JSON, HTML, or CSV file.')
    result = {}
    for name, content in sources:
        for raw_row in _parse_file(name, content):
            row = normalize(raw_row)
            if row:
                prev = result.get(row['url'])
                if prev is None:
                    result[row['url']] = row
                else:
                    for field in ('caption', 'hashtags', 'liked_at', 'media_file'):
                        if not prev[field] and row[field]:
                            prev[field] = row[field]
            if len(result) > MAX_ITEMS:
                raise ValueError('Too many liked items (limit 100,000).')
    return list(result.values())


def parse_manifest(raw):
    """Optional CSV enriched by user with url,caption,type,hashtags,media_file."""
    return [row for raw_row in _from_csv(raw) if (row := normalize(raw_row))]


def terms_from_query(query):
    # Commas and newlines separate phrases; otherwise whitespace separates words.
    return [t.strip().casefold() for t in re.split(r'[,\n]+', query) if t.strip()] if ',' in query or '\n' in query else [t.casefold() for t in query.split() if t.strip()]


def text_matches(item, terms, match_all=False):
    haystack = (item['caption'] + ' ' + item['hashtags']).casefold()
    predicates = [term in haystack or (term.startswith('#') and term[1:] in haystack) for term in terms]
    return (all(predicates) if match_all else any(predicates)) if terms else True
