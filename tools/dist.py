"""Pack game/ into dist/alans-bot-plugs.zip for an itch.io HTML5 upload: index.html at the zip's root."""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game")
DIST = os.path.join(ROOT, "dist")
OUT = os.path.join(DIST, "alans-bot-plugs.zip")
SKIP = {".DS_Store", "Thumbs.db", "desktop.ini"}


def main():
    if not os.path.isfile(os.path.join(GAME, "index.html")):
        sys.exit("game/index.html not found")
    os.makedirs(DIST, exist_ok=True)
    count = 0
    # Already-compressed media gain nothing from deflate; store them so the zip builds fast.
    stored = (".mp3", ".jpg", ".png", ".glb")
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for folder, dirs, files in os.walk(GAME):
            dirs[:] = sorted(d for d in dirs if not d.startswith((".", "_")))
            for name in sorted(files):
                if name in SKIP or name.startswith("."):
                    continue
                path = os.path.join(folder, name)
                arc = os.path.relpath(path, GAME).replace(os.sep, "/")
                kind = zipfile.ZIP_STORED if name.lower().endswith(stored) else zipfile.ZIP_DEFLATED
                z.write(path, arc, compress_type=kind)
                count += 1
    print(f"{os.path.relpath(OUT, ROOT).replace(os.sep, '/')}: {count} files, {os.path.getsize(OUT) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
