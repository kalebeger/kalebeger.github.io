"""Public route, navigation, asset, semantic HTML, and fragment checks."""
import argparse
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse
import build

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []
        self.active = []
        self.main_count = 0
        self.h1_count = 0
        self.nav_count = 0
        self.in_nav = False
        self.images = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'main':
            self.main_count += 1
        if tag == 'h1':
            self.h1_count += 1
        if tag == 'nav':
            self.in_nav = attrs.get('id') == 'main-nav'
        if tag == 'a' and self.in_nav:
            self.nav_count += 1
        if attrs.get('aria-current') == 'page':
            self.active.append(attrs.get('href'))
        for attr in ('href', 'src'):
            if attr in attrs:
                self.links.append(attrs[attr])
        if tag == 'img':
            self.images.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'nav':
            self.in_nav = False


def check(rebuild=True):
    if rebuild:
        build.build()
    output = build.OUT.resolve()
    pages = sorted(output.rglob('*.html'))
    assert {p.relative_to(output).as_posix() for p in pages} == set(build.PAGES)
    for path in pages:
        source = path.read_text()
        page = Page()
        page.feed(source)
        assert page.main_count == page.h1_count == 1, path
        assert page.nav_count == 6 and len(page.active) == 1, path
        assert len(page.ids) == len(set(page.ids)), path
        assert 'main' in page.ids and 'main-nav' in page.ids, path
        for image in page.images:
            assert image.get('alt'), path
            assert int(image.get('width', 0)) > 0 and int(image.get('height', 0)) > 0, path
        for link in page.links:
            parsed = urlparse(link)
            if parsed.scheme:
                assert parsed.scheme in ('https', 'http', 'mailto'), (path, link)
                continue
            target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            assert target.is_relative_to(output) and target.is_file(), (path, link)
            if parsed.fragment:
                linked = Page()
                linked.feed(target.read_text())
                assert parsed.fragment in linked.ids, (path, link)
        active = (path.parent / page.active[0]).resolve()
        expected = output / ('projects.html' if path.parent.name == 'projects' else path.name)
        assert active == expected, path
    print(f'PASS: {len(pages)} public pages; navigation, assets, headings, landmarks, fragments and alt text.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-build', action='store_true')
    check(not parser.parse_args().no_build)
