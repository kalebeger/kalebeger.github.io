"""Prepare a fresh, dependency-only dist artifact. Never overwrite preview files.

In a clean CI checkout: python3 -B prepare_public.py dist
Upload only that dist directory, never the repository or the local preview tree.
"""
import argparse
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

import build
from check import Page


def public_files(root):
    """Follow rendered HTML and CSS references, rather than copying asset folders."""
    pages = {Path(name) for name in build.render_pages()}
    pending = list(pages)
    selected = set()
    while pending:
        relative = pending.pop()
        if relative in selected:
            continue
        source = root / relative
        if not source.is_file() or source.is_symlink():
            raise ValueError('Missing or unsafe public resource: ' + str(relative))
        if relative not in pages and (relative.parts[0] != 'assets' or source.suffix.lower() not in
                {'.css', '.js', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.pdf'}):
            raise ValueError('Unexpected public resource: ' + str(relative))
        if relative.name == 'freas-hall-temporary.jpg':
            raise ValueError('Rights-unverified Freas Hall photograph cannot be published.')
        selected.add(relative)
        links = []
        if source.suffix == '.html':
            page = Page()
            page.feed(source.read_text())
            links = page.links
        elif source.suffix == '.css':
            css = source.read_text()
            if '@import' in css:
                raise ValueError('Review CSS imports before publishing.')
            links = re.findall(r'url\(\s*[\"\']?([^\)\"\']+)', css)
        for link in links:
            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (source.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(root.resolve()):
                raise ValueError('Public reference escapes export: ' + link)
            pending.append(target.relative_to(root.resolve()))
    return selected


def prepare(destination):
    destination = Path(destination).resolve()
    if not destination.is_relative_to(build.ROOT) or destination == build.ROOT:
        raise ValueError('Choose an empty output directory inside this project.')
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('Output must be empty. Existing previews and recovery files are never overwritten.')
    with tempfile.TemporaryDirectory(prefix='.build-test-release-', dir=build.ROOT) as temporary:
        staged = Path(temporary) / 'dist'
        build.build(staged)
        selected = public_files(staged)
        for relative in sorted(selected):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(staged / relative, target)
    print(f'Prepared {len(selected)} public files in {destination}')
    return selected


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', help='Empty project-local output directory (dist in a clean checkout)')
    prepare(parser.parse_args().output)
