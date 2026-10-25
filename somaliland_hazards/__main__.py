"""Command line:  python -m somaliland_hazards [run|watch|sample] [options]"""
import argparse
import logging
import time

from . import pipeline


def _print_alerts(alerts, status=None):
    bad = [k for k, v in (status or {}).items() if not (v == "ok" or v.startswith("skipped"))]
    if bad:
        print(f"!! Feeds unavailable: {', '.join(bad)} — alerts below may be incomplete.")
    if not alerts:
        print("No active alerts from the feeds that responded." if bad else "No active alerts.")
        return
    for a in alerts:
        print(f"[{a['level']:7}] {a['hazard']:<24} {a['title']}\n          {a['detail']}")


def serve(out_dir, port=8000):
    """Serve the output folder at http://localhost so every tile server accepts the requests
    (OpenStreetMap blocks pages opened straight from disk)."""
    import functools, http.server, socketserver, webbrowser
    from pathlib import Path
    folder = Path(out_dir).resolve()
    if not (folder / "map.html").exists():
        raise SystemExit(f"No map.html in {folder}. Run `python -m somaliland_hazards run` "
                         "(or `sample`) first.")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(folder))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        url = f"http://localhost:{port}/map.html"
        print(f"Serving {folder}\nOpen {url}  (Ctrl+C to stop)")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="somaliland_hazards",
                                 description="Somaliland multi-hazard monitor")
    ap.add_argument("command", nargs="?", default="run", choices=["run", "watch", "sample", "serve"],
                    help="run once, watch (repeat), sample (offline demo), or serve (open map in browser)")
    ap.add_argument("--out", default="output", help="output folder (default: output)")
    ap.add_argument("--firms-key", help="NASA FIRMS MAP_KEY (or env FIRMS_MAP_KEY)")
    ap.add_argument("--boundary", help="optional Somaliland boundary GeoJSON to draw")
    ap.add_argument("--every", type=int, default=30, help="minutes between runs in watch mode")
    ap.add_argument("--port", type=int, default=8000, help="port for serve (default 8000)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.command == "serve":
        serve(args.out, args.port)
        return

    if args.command == "sample":
        from .sample import sample_data
        data, status = sample_data()
        alerts, path = pipeline.write_outputs(data, status, args.out, args.boundary, sample=True)
        _print_alerts(alerts)
        print(f"\nSample map written to {path}")
        return

    while True:
        alerts, path, status = pipeline.run(args.out, args.firms_key, args.boundary)
        _print_alerts(alerts, status)
        print(f"\nMap written to {path}")
        if args.command != "watch":
            break
        time.sleep(args.every * 60)


if __name__ == "__main__":
    main()
