# Kaleb Eger — personal portfolio

Source for https://kalebeger.github.io/.

## Edit and build

The seven HTML files in `pages/` are the editable page sources. Images, the résumé PDF, navigation JavaScript, and CSS live in `assets/`. Update page writing in the appropriate HTML source and design in CSS; rebuild after changes. All tooling uses Python 3's standard library without installed packages.

```
python3 -B -m unittest test_public_site
python3 -B prepare_public.py dist
python3 -B check.py --no-build
```

The release command requires empty output and refuses to overwrite existing files. For local preview, run `python3 -B -m http.server 8000 --bind 127.0.0.1 --directory dist` and manually visit http://127.0.0.1:8000/. It does not open a browser. If port 8000 is already in use, use another port; do not stop other servers.

## Publication

`.github/workflows/pages.yml` runs manually and publishes only a clean `dist/` artifact. It first runs the production tests, builds the artifact, and checks every route and local link. Pages must use GitHub Actions as its publishing source. Deployment requires both the manual `publish` input and the repository variable `PORTFOLIO_PUBLISH_ENABLED=true`; publishing is disabled by default.

The public sources contain no editor application, concept previews, recovery data, development archives, or temporary Freas Hall photograph. The Experience page uses an optimized JPEG of Freas Hall photographed by Kaleb Eger; the original TIFF is kept outside this publication repository. Existing photo credits are retained; the owner has confirmed public-use permission for the seven supplied professional/event photographs. Oddfellows visuals are project screenshots, not a separate application source repository.
