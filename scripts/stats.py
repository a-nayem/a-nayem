"""Render assets/stats.svg from live GitHub data.

Run by .github/workflows/stats.yml with GH_TOKEN set. Standard library only.
Use --demo to render from the values read off the public profile page.
"""
import json, os, sys, urllib.request
from xml.sax.saxutils import escape as esc

USER = os.environ.get("GH_USER", "a-nayem")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "stats.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes { stargazerCount primaryLanguage { name } }
    }
    contributionsCollection {
      contributionCalendar { totalContributions }
      totalPullRequestContributions
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}", "Content-Type": "application/json"},
    )
    try:
        payload = json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        sys.exit(f"GitHub API HTTP {e.code}: {e.read().decode(errors='replace')}")
    if payload.get("errors") or not (payload.get("data") or {}).get("user"):
        sys.exit(f"GraphQL error: {json.dumps(payload.get('errors') or payload)}")
    u = payload["data"]["user"]
    langs = {}
    for n in u["repositories"]["nodes"]:
        if n["primaryLanguage"]:
            langs[n["primaryLanguage"]["name"]] = langs.get(n["primaryLanguage"]["name"], 0) + 1
    return {
        "repos": u["repositories"]["totalCount"],
        "followers": u["followers"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "contrib": u["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "prs": u["contributionsCollection"]["totalPullRequestContributions"],
        "langs": langs,
    }


BG, PANEL, LINE = "#050807", "#08110e", "#14302a"
GREEN, BLUE, TEXT, MUTED = "#22e58b", "#38bdf8", "#d7efe6", "#6f8f85"
MONO = "'JetBrains Mono','SFMono-Regular',Consolas,'DejaVu Sans Mono',monospace"
SERIF = "Georgia,'Times New Roman','DejaVu Serif',serif"


def t(x, y, s, size, fill, font=MONO, weight="normal", anchor="start", ls=0):
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}">{esc(str(s))}</text>')


def render(d):
    W, gap = 880, 10
    tiles = [("PUBLIC REPOS", d["repos"], GREEN), ("CONTRIBUTIONS", d["contrib"], BLUE),
             ("STARS", d["stars"], GREEN), ("FOLLOWERS", d["followers"], BLUE)]
    tw = (W - gap * 3) / 4
    langs = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:5]
    total = sum(v for _, v in langs) or 1
    H = 190 if langs else 100
    b = f'<defs><linearGradient id="a" x1="0" x2="1"><stop offset="0" stop-color="{GREEN}"/><stop offset="1" stop-color="{BLUE}"/></linearGradient></defs>'
    for i, (lab, val, col) in enumerate(tiles):
        x = i * (tw + gap)
        b += f'<rect x="{x}" y="0" width="{tw}" height="100" rx="10" fill="{PANEL}" stroke="{LINE}"/>'
        b += f'<rect x="{x+16}" y="0" width="28" height="3" fill="{col}"/>'
        b += t(x + 16, 62, "-" if val is None else val, 38, col, SERIF, "bold")
        b += t(x + 16, 86, lab, 10, TEXT, weight="bold", ls=1.5)
    if not langs:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
                f'aria-label="GitHub stats for {USER}"><title>GitHub stats for {USER}</title>{b}</svg>')
    b += f'<rect x="0" y="110" width="{W}" height="80" rx="10" fill="{PANEL}" stroke="{LINE}"/>'
    b += t(16, 134, "TOP LANGUAGES BY REPO COUNT", 10, BLUE, weight="bold", ls=2)
    x = 16.0; bw = W - 32
    cols = [GREEN, BLUE, "#1f9e73", "#0ea5e9", "#6f8f85"]
    for i, (n, v) in enumerate(langs):
        w = bw * v / total
        b += f'<rect x="{x:.1f}" y="146" width="{max(w-3,2):.1f}" height="8" rx="4" fill="{cols[i]}"/>'
        x += w
    lx = 16
    for i, (n, v) in enumerate(langs):
        b += f'<circle cx="{lx+4}" cy="176" r="4" fill="{cols[i]}"/>' + t(lx + 14, 180, f"{n} {v}", 11, TEXT)
        lx += 14 + (len(n) + 3) * 6.8 + 22
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="GitHub stats for {USER}"><title>GitHub stats for {USER}</title>{b}</svg>')


if __name__ == "__main__":
    if "--demo" in sys.argv:
        data = {"repos": 21, "followers": 4, "stars": 2, "contrib": None, "prs": 0,
                "langs": {}}
    else:
        data = fetch()
    open(OUT, "w").write(render(data))
    print("wrote", os.path.normpath(OUT), data)
