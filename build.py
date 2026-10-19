"""Build the portfolio from its seven approved HTML sources. Standard library only."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'dist'
PAGES = ('index.html', 'about.html', 'experience.html', 'projects.html',
         'projects/oddfellows.html', 'resume.html', 'contact.html')


def render_pages():
    return {name: (ROOT / 'pages' / name).read_text(encoding='utf-8') for name in PAGES}


def build(output=None):
    destination = Path(output) if output else OUT
    destination = destination.resolve()
    if not destination.is_relative_to(ROOT) or destination == ROOT:
        raise ValueError('Build output must be inside this project, outside its root.')
    for directory in ('pages', 'assets'):
        if any(p.is_symlink() for p in (ROOT / directory).rglob('*')):
            raise ValueError('Source symlinks are not supported.')
    pages = render_pages()
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'assets', destination / 'assets', dirs_exist_ok=True)
    for name, source in pages.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding='utf-8')
    print(f'Built {len(pages)} pages in {destination}')


if __name__ == '__main__':
    build()
