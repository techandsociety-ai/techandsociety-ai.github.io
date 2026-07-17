#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["livereload>=2.6"]
# ///
"""Local preview server for the techandsociety.ai site, with live reload.

Serves ``docs/`` (the deployed Pages source) and automatically reloads the
browser whenever a file under ``docs/`` changes — so you can edit an HTML file
and see it update without touching the browser.

Run it with uv — the dependency above is installed into an ephemeral,
cached environment automatically, no setup step::

    uv run serve.py                    # then open http://localhost:8000
    uv run serve.py --port 8080        # use a different port
    uv run serve.py --root website     # preview the (unpublished) website/ draft

No uv? Install livereload yourself and run it as a plain script::

    pip install livereload
    python3 serve.py

Prefer zero dependencies? ``python3 -m http.server`` from inside ``docs/`` also
works; you just have to reload the browser yourself.
"""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="port to serve on (default: 8000)"
    )
    parser.add_argument(
        "--root", default="docs", help="directory to serve (default: docs)"
    )
    parser.add_argument(
        "--host", default="localhost", help="host to bind (default: localhost)"
    )
    args = parser.parse_args()

    try:
        from livereload import Server
    except ImportError:
        sys.stderr.write(
            "livereload is not installed. The easy path is to run this with uv,\n"
            "which installs it automatically from the script's inline metadata:\n"
            "  uv run serve.py\n"
            "Or install it yourself:\n"
            "  pip install livereload && python3 serve.py\n"
            "Or serve without live reload:\n"
            f"  cd {args.root} && python3 -m http.server {args.port}\n"
        )
        return 1

    server = Server()
    # docs/ is a flat directory of static files; watch files one and two levels
    # deep so edits (and any future subfolders like docs/assets/) trigger a reload.
    server.watch(f"{args.root}/*")
    server.watch(f"{args.root}/*/*")
    print(f"Serving {args.root}/ at http://{args.host}:{args.port} (Ctrl-C to stop)")
    server.serve(root=args.root, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
