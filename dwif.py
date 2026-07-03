import math
from PIL import Image

REFERENCE_SIZE = 512
AUTO_TOP_STRIP_BASE = 17
AUTO_RADIUS_BASE = 36
_REF_FACTOR = math.sqrt(1844 * 853) / REFERENCE_SIZE
AUTO_TOP_STRIP_EXPONENT = math.log(54 / 17) / math.log(_REF_FACTOR)
AUTO_RADIUS_EXPONENT = math.log(172 / 36) / math.log(_REF_FACTOR)


def auto_value(base: float, exponent: float, width: int, height: int) -> int:
    size_factor = math.sqrt(width * height) / REFERENCE_SIZE
    return max(0, round(base * size_factor ** exponent))


def widget_fix(image: Image.Image, top_strip: int = None, radius: int = None) -> Image.Image:
    image = image.convert("RGBA")
    width, height = image.size

    if top_strip is None:
        top_strip = auto_value(AUTO_TOP_STRIP_BASE, AUTO_TOP_STRIP_EXPONENT, width, height)
    if radius is None:
        radius = auto_value(AUTO_RADIUS_BASE, AUTO_RADIUS_EXPONENT, width, height)

    image_height = max(height - top_strip, 0)
    radius = min(radius, width, image_height)

    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    out.paste(image, (0, top_strip))

    if radius > 0:
        px = out.load()
        r2 = radius * radius
        corner_x = width - radius
        for local_y in range(radius):
            dy = local_y + 0.5 - radius
            clear_start = radius
            for local_x in range(radius):
                dx = local_x + 0.5
                if dx * dx + dy * dy > r2:
                    clear_start = local_x
                    break
            if clear_start >= radius:
                continue
            y = top_strip + local_y
            for local_x in range(clear_start, radius):
                px[corner_x + local_x, y] = (0, 0, 0, 0)

    return out
