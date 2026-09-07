"""Generates the diamond-pendant reveal path: N evenly (arc-length) spaced
points along an idealized gem silhouette with a small hexagonal hanging
loop ("bail") on top, plus a jittered "wrong" counterpart for each point
used to draw a scrambled line when a team makes a mistake. Same
idealized-template / arc-length-resample technique as the rocket and star
reveal games.
"""
import math, random

# gem body: flat "table" top (split at its midpoint so the bail's neck can
# drop straight down the CENTER instead of connecting to a corner — an
# off-center connection produced a stray diagonal line through the loop
# during prototyping), crown/girdle, pavilion tapering to a point.
_GEM = [
    ("TopCenter", 0, -70),
    ("TopRight", 50, -70),
    ("GirdleRight", 95, -20),
    ("Point", 0, 110),
    ("GirdleLeft", -95, -20),
    ("TopLeft", -50, -70),
]

# small hexagonal "bail" (hanging loop), its own closed loop starting and
# ending at BailBottom — the point closest to the gem — so the connecting
# neck is a short, clean, perfectly vertical segment right through the
# middle of the ring rather than cutting across it.
_BAIL = [
    ("BailBottom", 0, -76),
    ("BailLowerLeft", -18, -88),
    ("BailUpperLeft", -18, -112),
    ("BailTop", 0, -124),
    ("BailUpperRight", 18, -112),
    ("BailLowerRight", 18, -88),
]

def _subdivide_loop(points, n_extra=1):
    out = []
    n = len(points)
    for i in range(n):
        name_a, ax, ay = points[i]
        _, bx, by = points[(i + 1) % n]
        out.append((name_a, ax, ay))
        for k in range(1, n_extra + 1):
            t = k / (n_extra + 1)
            out.append((f"{name_a}-mid{k}", ax + (bx - ax) * t, ay + (by - ay) * t))
    return out

_bail_sub = _subdivide_loop(_BAIL, n_extra=1)
_bail_closed = _bail_sub + [_bail_sub[0]]      # closes back at BailBottom

_gem_sub = _subdivide_loop(_GEM, n_extra=3)
_gem_closed = _gem_sub + [_gem_sub[0]]         # closes back at TopCenter

_FULL_LOCAL = [(x, y) for _, x, y in (_bail_closed + _gem_closed)]  # 38 idealized points

# scale/center into the shared 500x420 canvas frame (same viewBox as the
# rocket and star games)
_xs = [p[0] for p in _FULL_LOCAL]
_ys = [p[1] for p in _FULL_LOCAL]
_w, _h = max(_xs) - min(_xs), max(_ys) - min(_ys)
_scale = min(320 / _w, 360 / _h)
_ox = (500 - _w * _scale) / 2 - min(_xs) * _scale
_oy = (420 - _h * _scale) / 2 - min(_ys) * _scale
DIAMOND_VERTICES = [(round(x * _scale + _ox, 1), round(y * _scale + _oy, 1)) for x, y in _FULL_LOCAL]


def _cum_lengths(pts):
    lens = [0.0]
    for i in range(len(pts) - 1):
        lens.append(lens[-1] + math.dist(pts[i], pts[i + 1]))
    return lens

def _point_at(pts, lens, target):
    for i in range(len(lens) - 1):
        if lens[i] <= target <= lens[i + 1]:
            seg = lens[i + 1] - lens[i]
            t = 0 if seg == 0 else (target - lens[i]) / seg
            x = pts[i][0] + t * (pts[i + 1][0] - pts[i][0])
            y = pts[i][1] + t * (pts[i + 1][1] - pts[i][1])
            return (round(x, 1), round(y, 1))
    return pts[-1]

# Hand-tuned exact layout for the default 38-question deck — verified-good
# fixed layout (see geometry_diamond5.py prototype). Arc-length-resampling
# the whole vertex list is used only as a fallback for a different question
# count, same pattern as the star-reveal game.
DIAMOND_POINTS_38 = list(DIAMOND_VERTICES)

def diamond_points(n=38):
    if n == 38:
        return list(DIAMOND_POINTS_38)
    lens = _cum_lengths(DIAMOND_VERTICES)
    total = lens[-1]
    pts = []
    for i in range(n):
        target = total * i / (n - 1)
        pts.append(_point_at(DIAMOND_VERTICES, lens, target))
    return pts

def wrong_points(correct_pts, seed=13, jitter=50):
    random.seed(seed)
    out = []
    cx, cy = 250, 210
    for (x, y) in correct_pts:
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy) or 1
        nx, ny = dx / dist, dy / dist
        ang = random.uniform(-0.9, 0.9)
        rx = nx * math.cos(ang) - ny * math.sin(ang)
        ry = nx * math.sin(ang) + ny * math.cos(ang)
        mag = random.uniform(jitter * 0.6, jitter * 1.3)
        out.append((round(x + rx * mag, 1), round(y + ry * mag, 1)))
    return out

if __name__ == "__main__":
    pts = diamond_points(38)
    wpts = wrong_points(pts)
    print("n:", len(pts))
    print("CORRECT:", pts)
    print("WRONG:  ", wpts)
    mind = min(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    print("min consecutive spacing:", round(mind, 1))
