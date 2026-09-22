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
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="300" viewBox="0 0 1000 300" role="img" aria-labelledby="title">',
        '<title id="title">Stars from ' + html.escape(username) + ' contribution history</title>',
        '<defs><radialGradient id="glow"><stop stop-color="#ffffff" stop-opacity=".38"/><stop offset=".28" stop-color="#e5efff" stop-opacity=".12"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient></defs>',
        '<rect width="1000" height="300" fill="#000000"/>']
    pitch = 880 / max(len(weeks)-1, 1)
    stars = []
    for wi, week in enumerate(weeks):
        for day in week['contributionDays']:
            if day['contributionCount'] <= 0:
                continue
            level = LEVELS.index(day['contributionLevel'])
            x, y = 60 + wi * pitch, 60 + day['weekday'] * 30
            r = .85 + level * .32
            stars.append((x, y))
            svg.append(f'<g><title>{day["date"]}: {day["contributionCount"]} contributions</title>')
            svg.append(f'<circle cx="{x:.2f}" cy="{y}" r="{5+level*1.8:.2f}" fill="url(#glow)"/>')
            svg.append(f'<circle cx="{x:.2f}" cy="{y}" r="{r:.2f}" fill="#ffffff" opacity="{.6+level*.1:.2f}"/>')
            svg.append('</g>')
    links = []
    for i, (x, y) in enumerate(stars):
        nearby = [(j, px, py) for j, (px, py) in enumerate(stars[:i])
                  if (px-x)**2 + (py-y)**2 <= 100**2]
        if nearby:
            j, px, py = min(nearby, key=lambda p:(p[1]-x)**2+(p[2]-y)**2)
            links.append(f'<line data-a="{j}" data-b="{i}" x1="{px:.2f}" y1="{py}" x2="{x:.2f}" y2="{y}" stroke="#ffffff" stroke-opacity=".2" stroke-width=".65"/>')
    svg[4:4] = links
    svg.append('</svg>')
    return '\n'.join(svg)+'\n'


if __name__ == '__main__':
    username = os.environ.get('PROFILE_USERNAME', 'ZPRRR2004')
    calendar = fetch_calendar(username)
    output = ROOT / 'assets/contribution-constellation.svg'
    output.parent.mkdir(exist_ok=True)
    output.write_text(render(calendar, username), encoding='utf-8')
    print(f'Rendered {calendar["totalContributions"]} contributions to {output}')
