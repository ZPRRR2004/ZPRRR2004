"""Render the authenticated GitHub contribution calendar with stdlib only."""
import datetime as dt
import html
import hashlib
import re
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
    import random
    rng = random.Random(27)
    weeks = calendar['weeks']
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="360" viewBox="0 0 1000 360" role="img" aria-labelledby="title">',
        '<title id="title">Stars from ' + html.escape(username) + ' contribution history</title>',
        '<defs><radialGradient id="nebula"><stop stop-color="#182443" stop-opacity=".65"/><stop offset=".48" stop-color="#0a1026" stop-opacity=".4"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient><radialGradient id="violet"><stop stop-color="#251736" stop-opacity=".4"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient><radialGradient id="glow"><stop stop-color="#eef8ff" stop-opacity=".7"/><stop offset=".12" stop-color="#bfdfff" stop-opacity=".4"/><stop offset=".35" stop-color="#78aaff" stop-opacity=".12"/><stop offset="1" stop-color="#5799ff" stop-opacity="0"/></radialGradient><linearGradient id="ray"><stop stop-color="#b3daff" stop-opacity="0"/><stop offset=".5" stop-color="#eef8ff" stop-opacity=".8"/><stop offset="1" stop-color="#b3daff" stop-opacity="0"/></linearGradient></defs>',
        '<rect width="1000" height="360" fill="#000"/>',
        '<ellipse cx="580" cy="220" rx="420" ry="150" transform="rotate(-17 580 220)" fill="url(#nebula)"/>',
        '<ellipse cx="310" cy="180" rx="270" ry="110" transform="rotate(-22 310 180)" fill="url(#violet)"/>']
    # Faint decorative background dust is distinct from the larger contribution stars.
    for i in range(320):
        x, y = rng.uniform(14,986), rng.uniform(12,348)
        r = rng.uniform(.25,.8)
        svg.append(f'<circle data-dust="true" cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="#b9cde6" opacity="{rng.uniform(.1,.45):.2f}"/>')
    stars = []
    pitch = 880 / max(len(weeks)-1, 1)
    for wi, week in enumerate(weeks):
        for day in week['contributionDays']:
            if day['contributionCount'] <= 0:
                continue
            level = LEVELS.index(day['contributionLevel'])
            x, y = 60 + wi * pitch, 75 + day['weekday'] * 35
            stars.append((x,y,level,day))
    for i, (x,y,_,_) in enumerate(stars):
        nearby = [(j,px,py) for j,(px,py,_,_) in enumerate(stars[:i]) if (px-x)**2+(py-y)**2 <= 115**2]
        if nearby:
            j,px,py = min(nearby,key=lambda p:(p[1]-x)**2+(p[2]-y)**2)
            svg.append(f'<line data-a="{j}" data-b="{i}" x1="{px:.2f}" y1="{py}" x2="{x:.2f}" y2="{y}" stroke="#a2c7ef" stroke-opacity=".22" stroke-width=".65"/>')
    for x,y,level,day in stars:
        r, halo = .8+level*.3, 10+level*4
        svg.append(f'<g data-star="true"><title>{day["date"]}: {day["contributionCount"]} contributions</title>')
        svg.append(f'<circle cx="{x:.2f}" cy="{y}" r="{halo}" fill="url(#glow)"/>')
        svg.append(f'<circle cx="{x:.2f}" cy="{y}" r="{r:.2f}" fill="#f3f8ff"/>')
        if level >= 2:
            arm = 3+level*2
            svg.append(f'<rect x="{x-arm:.2f}" y="{y-.35:.2f}" width="{arm*2}" height=".7" fill="url(#ray)"/>')
            svg.append(f'<rect x="{x-arm:.2f}" y="{y-.35:.2f}" width="{arm*2}" height=".7" fill="url(#ray)" transform="rotate(90 {x:.2f} {y})"/>')
        svg.append('</g>')
    svg.append('</svg>')
    return '\n'.join(svg)+'\n'


if __name__ == '__main__':
    username = os.environ.get('PROFILE_USERNAME', 'ZPRRR2004')
    calendar = fetch_calendar(username)
    output = ROOT / 'assets/contribution-constellation.svg'
    output.parent.mkdir(exist_ok=True)
    output.write_text(render(calendar, username), encoding='utf-8')
    # Give each rendered image a distinct URL so profile image caches refresh.
    digest = hashlib.sha256(output.read_bytes()).hexdigest()[:16]
    readme = ROOT / 'README.md'
    if readme.exists():
        text = readme.read_text(encoding='utf-8')
        text = re.sub(r'(assets/contribution-constellation\\.svg)(?:\\?v=[a-zA-Z0-9_-]+)?', lambda match: match.group(1) + '?v=' + digest, text)
        readme.write_text(text, encoding='utf-8')
    print(f'Rendered {calendar["totalContributions"]} contributions to {output}')
