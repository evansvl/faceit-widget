import io
import os
import httpx
from PIL import Image, ImageOps
from dwif import widget_fix

TARGET = (512, 512)
SRC_BASE = "https://raw.githubusercontent.com/ghostcap-gaming/cs2-map-images/main/cs2"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps")

MAPS = [
    "de_ancient", "de_anubis", "de_basalt", "de_brewery", "de_cache",
    "de_dogtown", "de_dust2", "de_edin", "de_golden", "de_grail",
    "de_inferno", "de_jura", "de_mills", "de_mirage", "de_nuke",
    "de_overpass", "de_palacio", "de_poseidon", "de_rooftop", "de_sanctum",
    "de_stronghold", "de_thera", "de_train", "de_vertigo",
    "cs_agency", "cs_alpine", "cs_italy", "cs_office",
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for name in MAPS:
            resp = client.get(f"{SRC_BASE}/{name}.png")
            if resp.status_code != 200:
                print(f"skip {name}: {resp.status_code}")
                continue
            src = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            framed = ImageOps.fit(src, TARGET, method=Image.LANCZOS, centering=(0.5, 0.5))
            out = widget_fix(framed)
            out.save(os.path.join(OUT_DIR, f"{name}.webp"), "WEBP", quality=90, method=6)
            print(f"ok {name}: {out.size}")


if __name__ == "__main__":
    main()
