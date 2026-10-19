"""Public-site regressions, independent of the retired visual editor's tests."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
import contextlib
import io
import tempfile
import unittest

import build
import prepare_public
from check import Page


class PublicSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='.build-test-public-', dir=build.ROOT)
        cls.output = Path(cls.temp.name) / 'public'
        with contextlib.redirect_stdout(io.StringIO()):
            build.build(cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def pages(self):
        return sorted(self.output.rglob('*.html'))

    def test_fresh_export_contains_only_public_routes(self):
        self.assertEqual(len(self.pages()), 7)
        for path in self.output.rglob('*'):
            self.assertNotIn(path.suffix, ('.py', '.json', '.command'))
            self.assertNotIn('concepts', path.relative_to(self.output).parts)
            self.assertNotIn('editor', path.relative_to(self.output).parts)
        for path in self.pages():
            source = path.read_text()
            for private_marker in ('data-field=', 'data-style-block=', '/api/', 'contenteditable='):
                self.assertNotIn(private_marker, source)

    def test_links_remain_inside_github_pages_project_prefix(self):
        base = 'https://example.github.io/personal-website/'
        for path in self.pages():
            parsed = Page()
            parsed.feed(path.read_text())
            for link in parsed.links:
                if urlparse(link).scheme:
                    continue
                target = urlparse(urljoin(base + path.relative_to(self.output).as_posix(), link))
                self.assertTrue(target.path.startswith('/personal-website/'), (path, link))
                relative = unquote(target.path.removeprefix('/personal-website/'))
                self.assertTrue((self.output / relative).is_file(), (path, link))
                # Check spelling/case as Linux hosting will, even on macOS.
                directory = self.output
                for part in Path(relative).parts:
                    self.assertIn(part, [child.name for child in directory.iterdir()])
                    directory /= part

    def test_images_reserve_intrinsic_space_and_keep_alt_text(self):
        for path in self.pages():
            parsed = Page()
            parsed.feed(path.read_text())
            for image in parsed.images:
                self.assertTrue(image.get('alt'))
                self.assertGreater(int(image.get('width', 0)), 0)
                self.assertGreater(int(image.get('height', 0)), 0)


    def test_pdf_view_download_and_fallback_use_same_existing_document(self):
        class Links(HTMLParser):
            def __init__(self):
                super().__init__()
                self.links, self.frames = [], []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'a' and '.pdf' in attrs.get('href', ''):
                    self.links.append(attrs)
                if tag == 'iframe':
                    self.frames.append(attrs)

        parsed = Links()
        parsed.feed((self.output / 'resume.html').read_text())
        self.assertEqual(len(parsed.frames), 1)
        pdf = parsed.frames[0]['src']
        self.assertTrue(parsed.frames[0].get('title'))
        self.assertTrue((self.output / pdf).read_bytes().startswith(b'%PDF-'))
        self.assertTrue(any('download' in link for link in parsed.links))
        self.assertTrue(any(link.get('target') == '_blank' for link in parsed.links))
        self.assertTrue(all(link['href'] == pdf for link in parsed.links))

    def test_freas_hall_uses_owned_optimized_photo_without_placeholder(self):
        source = (self.output / 'experience.html').read_text()
        self.assertNotIn('experience-photo-pending', source)
        self.assertNotIn('Photograph to come.', source)
        self.assertIn('Photograph by Kaleb Eger.', source)
        parsed = Page()
        parsed.feed(source)
        image = next(image for image in parsed.images if image['src'] == 'assets/media/freas-hall.jpg')
        self.assertEqual((image['width'], image['height']), ('1600', '1000'))
        payload = (self.output / image['src']).read_bytes()
        self.assertTrue(payload.startswith(b'\xff\xd8'))
        self.assertLess(len(payload), 1000000)
        self.assertFalse(any(p.suffix.lower() in ('.tif', '.tiff') for p in self.output.rglob('*')))
        self.assertNotIn('freas-hall-temporary.jpg', source)
        self.assertFalse((self.output / 'assets/media/freas-hall-temporary.jpg').exists())

    def test_release_is_only_reachable_public_dependencies(self):
        release = Path(self.temp.name) / 'release/dist'
        with contextlib.redirect_stdout(io.StringIO()):
            selected = prepare_public.prepare(release)
        self.assertEqual(selected, {p.relative_to(release) for p in release.rglob('*') if p.is_file()})
        self.assertEqual(selected, prepare_public.public_files(release))
        self.assertEqual(len(list(release.rglob('*.html'))), 7)
        for excluded in ('assets/home-geometry.css', 'assets/editorial.css', 'assets/home.css',
                         'assets/site.css', 'assets/media/freas-hall-temporary.jpg',
                         '.portfolio-preview.json', 'concepts/refined.html'):
            self.assertFalse((release / excluded).exists(), excluded)
        for page in self.pages():
            self.assertEqual(page.read_bytes(), (release / page.relative_to(self.output)).read_bytes())
        with self.assertRaisesRegex(ValueError, 'Output must be empty'):
            prepare_public.prepare(release)

    def test_contact_destinations_are_approved_and_safe(self):
        source = (self.output / 'contact.html').read_text()
        self.assertIn('href="mailto:kre004@bucknell.edu"', source)
        self.assertIn('href="https://www.linkedin.com/in/kalebeger" target="_blank" rel="noopener noreferrer"', source)

    def test_only_documented_photo_credit_is_displayed(self):
        about = (self.output / 'about.html').read_text()
        self.assertEqual(about.count('Photo Credit:'), 4)
        self.assertEqual(about.count('Photo Credit: Milton Area School District'), 1)
        self.assertEqual(about.count('Photo Credit: Bucknell University'), 2)
        self.assertIn('Photo Credit: Emily Lamparter / Bucknell University', about)
        home = (self.output / 'index.html').read_text()
        self.assertEqual(home.count('Photo Credit:'), 1)
        self.assertIn('Photo Credit: Emily Lamparter / Bucknell University', home)
        for page in self.pages():
            if page.name not in ('about.html', 'index.html'):
                self.assertNotIn('Photo Credit:', page.read_text())



    def test_root_domain_links_and_fragment_checks(self):
        base = 'https://kalebeger.github.io/'
        for path in self.pages():
            page = Page()
            page.feed(path.read_text())
            for link in page.links:
                if urlparse(link).scheme:
                    continue
                target = urlparse(urljoin(base + path.relative_to(self.output).as_posix(), link))
                self.assertEqual(target.netloc, 'kalebeger.github.io')
                self.assertFalse(target.path.startswith('/personal-website/'))
                resource = self.output / unquote(target.path.lstrip('/'))
                self.assertTrue(resource.is_file(), (path, link))
                if target.fragment:
                    linked = Page()
                    linked.feed(resource.read_text())
                    self.assertIn(target.fragment, linked.ids)

    def test_build_has_no_retired_modules_or_private_content(self):
        for name in ('editor', 'editor_server.py', 'editor_store.py', 'editor_content.py',
                     'builder_design.py', 'content_management.py', 'concept-previews',
                     'content', 'Eger Resume.pdf'):
            self.assertFalse((build.ROOT / name).exists(), name)
        for route, source in build.render_pages().items():
            self.assertEqual(source, (self.output / route).read_text())


if __name__ == '__main__':
    unittest.main()
