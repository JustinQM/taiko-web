# Read-only leaderboard, served under /highscores by the stack's nginx.
#
# Built with the repository root as its context, not this directory,
# because tnt.woff2 is generated here from public/assets/fonts/TnT.ttf
# rather than committed. That font is a 4.7MB full-range face; the page
# only needs Latin, digits and a handful of symbols for its headings, and
# the subset comes to 12KB.
FROM docker.io/library/python:3.11-slim AS font

RUN pip install --no-cache-dir fonttools brotli
WORKDIR /font
COPY public/assets/fonts/TnT.ttf ./
# Ranges chosen to match what the stylesheet actually renders: ASCII, the
# multiplication sign, curly quotes, the ellipsis, arrows, the star pair
# and the four CJK codepoints in the page furniture.
RUN pyftsubset TnT.ttf --output-file=tnt.woff2 --flavor=woff2 \
    --unicodes="U+0020-007E,U+00D7,U+2018-2019,U+201C-201D,U+2026,U+2190-2193,U+2605-2606,U+592A,U+9F13,U+FF0C,U+FF0E" \
    --layout-features='' --no-hinting --desubroutinize


FROM docker.io/library/python:3.11-slim

RUN pip install --no-cache-dir flask pymongo gunicorn
WORKDIR /app
COPY highscores/app.py highscores/data.py ./
COPY highscores/templates/ templates/
COPY highscores/static/ static/
COPY --from=font /font/tnt.woff2 static/tnt.woff2

EXPOSE 8000
CMD ["gunicorn", "-b", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "app:app"]
