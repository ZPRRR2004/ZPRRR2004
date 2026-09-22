"""Render the authenticated GitHub contribution calendar with stdlib only."""
import datetime as dt
import html
import json
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ['NONE', 'FIRST_QUARTILE', 'SECOND_QUARTILE', 'THIRD_QUARTILE', 'FOURTH_QUARTILE']
COLORS = ['#26334b', '#638abb', '#79b7d7', '#a7dfec', '#fff0bc']


def fetch_calendar(username):
    query = '''query($login:String!) { user(login:$login) {
      contributionsCollection { contributionCalendar { totalContributions
        weeks { contributionDays { date weekday contributionCount contributionLevel } }
      } }
    } }'''
    req = urllib.request.Request('https://api.github.com/graphql',
        data=json.dumps({'query': query, 'variables': {'login': username}}).encode(),
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Content-Type': 'application/json', 'User-Agent': 'contribution-constellation'})
    with urllib.request.urlopen(req, timeout=45) as response:
        payload = json.load(response)
    if payload.get('errors'):
        raise RuntimeError(payload['errors'])
    calendar = payload['data']['user']['contributionsCollection']['contributionCalendar']
    if not calendar['weeks']:
        raise ValueError('Empty contribution calendar; preserving previous image')
    return calendar


def render(calendar, username):
    weeks = calendar['weeks']
    days = [d for w in weeks for d in w['contributionDays']]
    active = sum(d['contributionCount'] > 0 for d in days)
    total = calendar['totalContributions']
    esc = html.escape
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="420" viewBox="0 0 1000 420" role="img" aria-labelledby="title desc">',
        '<title id="title">Contribution Constellation</title>',
        f'<desc id="desc">{esc(username)}: {total} contributions across {active} active days. Each star is one day; brightness follows contribution activity.</desc>',
        '<defs><radialGradient id="sky"><stop stop-color="#17233b"/><stop offset="1" stop-color="#080e1b"/></radialGradient>',
        '<radialGradient id="halo"><stop stop-color="#9adaff" stop-opacity=".4"/><stop offset="1" stop-color="#9adaff" stop-opacity="0"/></radialGradient></defs>',
        '<rect x="1" y="1" width="998" height="418" rx="20" fill="url(#sky)" stroke="#26324a"/>',
        '<g font-family="Segoe UI,Arial,sans-serif">',
        '<text x="44" y="42" fill="#8ba5c5" font-size="11" letter-spacing="3">THE OBSERVATORY / ZPRRR2004</text>',
        '<text x="44" y="84" fill="#edf4ff" font-size="30" font-weight="600">Contribution Constellation</text>',
        '<text x="44" y="110" fill="#93a6bf" font-size="13">Small steps. A growing universe.</text>',
        f'<text x="954" y="64" text-anchor="end" fill="#fff0bc" font-size="26">{total:,}</text>',
        '<text x="954" y="86" text-anchor="end" fill="#93a6bf" font-size="11" letter-spacing="1">CONTRIBUTIONS</text>']
    pitch = min(17, 884 / max(len(weeks)-1, 1))
    stars = []
    last_month = None
    last_label_x = -100
    for wi, week in enumerate(weeks):
        for day in week['contributionDays']:
            date = dt.date.fromisoformat(day['date'])
            x, y = 66 + wi * pitch, 166 + day['weekday'] * 21
            month = date.strftime('%b')
            if month != last_month:
                if wi < len(weeks)-2 and x - last_label_x >= 38:
                    svg.append(f'<text x="{x:.1f}" y="143" fill="#70849f" font-size="10">{month}</text>')
                    last_label_x = x
                last_month = month
            level = LEVELS.index(day['contributionLevel'])
            if level:
                stars.append((x,y,level,day))
            else:
                svg.append(f'<rect x="{x-2:.1f}" y="{y-2}" width="4" height="4" rx="1" fill="#26334b" opacity=".7"/>')
    # Short links are decorative only; day positions stay on the real calendar.
    for i, (x,y,level,day) in enumerate(stars):
        nearby = [(px,py) for px,py,_,_ in stars[:i] if 0 < x-px <= pitch*3 and abs(y-py) <= 45]
        if nearby:
            px,py = min(nearby, key=lambda p:(p[0]-x)**2+(p[1]-y)**2)
            svg.append(f'<path d="M {px:.1f} {py} L {x:.1f} {y}" stroke="#7196c7" stroke-width=".8" opacity=".23"/>')
    for x,y,level,day in stars:
        r = 1.5 + level*.65
        svg.append(f'<g><title>{day["date"]}: {day["contributionCount"]} contributions</title>')
        svg.append(f'<circle cx="{x:.1f}" cy="{y}" r="{5+level*2}" fill="url(#halo)"/>')
        svg.append(f'<circle cx="{x:.1f}" cy="{y}" r="{r}" fill="{COLORS[level]}"/>')
        if level == 4:
            svg.append(f'<path d="M {x-7:.1f} {y} H {x+7:.1f} M {x:.1f} {y-7} V {y+7}" stroke="#fff0bc" opacity=".7" stroke-width=".8"/>')
        svg.append('</g>')
    svg += ['<path d="M44 325 H956" stroke="#253149"/>',
        f'<text x="44" y="355" fill="#c2d1e6" font-size="13">{active} active days / {len(days)} days mapped</text>',
        f'<text x="44" y="382" fill="#70849f" font-size="11">{days[0]["date"]} — {days[-1]["date"]} · GitHub contribution data</text>',
        '<text x="760" y="355" fill="#8ba5c5" font-size="11">QUIET</text>',
        '<text x="916" y="355" fill="#8ba5c5" font-size="11">BRIGHT</text>']
    for i,c in enumerate(COLORS):
        svg.append(f'<circle cx="{815+i*20}" cy="351" r="{2+i*.6}" fill="{c}"/>')
    svg.append('</g></svg>')
    return '\n'.join(svg)+'\n'


if __name__ == '__main__':
    username = os.environ.get('PROFILE_USERNAME', 'ZPRRR2004')
    calendar = fetch_calendar(username)
    output = ROOT / 'assets/contribution-constellation.svg'
    output.parent.mkdir(exist_ok=True)
    output.write_text(render(calendar, username), encoding='utf-8')
    print(f'Rendered {calendar["totalContributions"]} contributions to {output}')
