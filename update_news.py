#!/usr/bin/env python3
"""Gather RSS metadata and make a source-attributed, 7-day static news feed.
Never generates or fabricates news, market prices, or causal explanations.
"""
from __future__ import annotations
import calendar
import hashlib
import html
import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
import feedparser
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
NOW = datetime.now(timezone.utc)
SOURCES = [
    ('BBC Business', 'https://feeds.bbci.co.uk/news/business/rss.xml', 'Markets'),
    ('BBC World', 'https://feeds.bbci.co.uk/news/world/rss.xml', 'World'),
    ('CNBC Markets', 'https://www.cnbc.com/id/20910258/device/rss/rss.html', 'Markets'),
    ('CNBC Economy', 'https://www.cnbc.com/id/10001147/device/rss/rss.html', 'Economy'),
    ('CNBC Technology', 'https://www.cnbc.com/id/19854910/device/rss/rss.html', 'Technology'),
    ('The Guardian Business', 'https://www.theguardian.com/uk/business/rss', 'Markets'),
    ('The Guardian World', 'https://www.theguardian.com/world/rss', 'World'),
    ('Federal Reserve', 'https://www.federalreserve.gov/feeds/press_all.xml', 'Economy'),
    ('SEC Press Releases', 'https://www.sec.gov/news/pressreleases.rss', 'Companies'),
]
CATEGORIES = ['Markets', 'Economy', 'Companies', 'Technology', 'World', 'Energy']
WORDS = {
 'Economy': ['fed', 'federal reserve', 'interest rate', 'inflation', 'consumer price', 'cpi', 'jobs report', 'employment', 'unemployment', 'treasury', 'gdp', 'central bank', 'recession', 'bond yields', 'economic'],
 'Technology': ['nvidia', 'artificial intelligence', ' ai ', 'semiconductor', 'chipmaker', 'chips', 'micron', 'openai', 'microsoft', 'quantum', 'software', 'data center', 'apple', 'google', 'tech stocks'],
 'Companies': ['earnings', 'quarterly', 'profit', 'revenue', 'shares', 'ipo', 'merger', 'acquisition', 'stock', 'company', 'investors', 'dividend', 'guidance', 'ceo'],
 'Energy': ['oil', 'crude', 'opec', 'gas prices', 'natural gas', 'energy', 'petroleum', 'lng'],
 'World': ['war', 'military', 'sanctions', 'election', 'tariff', 'trade deal', 'china', 'russia', 'ukraine', 'iran', 'israel', 'conflict', 'geopolitical', 'middle east'],
 'Markets': ['wall street', 'nasdaq', 's&p', 'stocks', 'market', 'dow jones', 'equities', 'futures', 'trading', 'investor', 'rally', 'selloff', 'market cap']
}
IMPORTANT = ['federal reserve', 'interest rate', 'inflation', 'jobs report', 'tariffs', 'earnings', 'recession', 'sanctions', 'trade war', 'oil prices', 'breaking', 'emergency', 'central bank', 'export controls', 'war', 'gdp']
STOP = set('the a an and or of to in on for from with at as by is are was were will has have had its it this that after before amid over into how why what who than new says said about latest more could should may can us uk u s'.split())
UA = {'User-Agent': 'MarketBriefPersonalNews/1.0 (personal RSS aggregation; contact via GitHub repo)', 'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*'}

def read_json(path, fallback):
    try: return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError): return fallback

def clean(value, limit=240):
    value = re.sub(r'<[^>]*>', ' ', str(value or ''))
    value = html.unescape(value)
    value = re.sub(r'\s+', ' ', value).strip()
    return value[:limit].rstrip(' ,;:') + ('…' if len(value)>limit else '')

def published(entry):
    for key in ('published_parsed', 'updated_parsed'):
        v = entry.get(key)
        if v:
            try: return datetime.fromtimestamp(calendar.timegm(v), tz=timezone.utc)
            except (ValueError, OverflowError, TypeError): pass
    for key in ('published', 'updated'):
        try: return parsedate_to_datetime(entry[key]).astimezone(timezone.utc)
        except (KeyError, ValueError, TypeError): pass
    return NOW

def categorize(title, fallback):
    low = ' '+title.lower()+' '
    score = {c: sum(2 if term in IMPORTANT else 1 for term in terms if term in low) for c, terms in WORDS.items()}
    winner = max(CATEGORIES, key=lambda c: score[c])
    return winner if score[winner] else fallback

def signature(title):
    return set(t for t in re.findall(r'[a-z0-9]+', title.lower()) if len(t)>2 and t not in STOP)

def score_story(s):
    age = max(0, (NOW-datetime.fromisoformat(s['published'].replace('Z','+00:00'))).total_seconds()/3600)
    q = s['title'].lower()
    priority = sum(4 for term in IMPORTANT if term in q)
    category_bonus = {'Economy':5,'Markets':4,'World':3,'Technology':3,'Energy':3,'Companies':2}.get(s['category'],0)
    return round(max(0, 28-age/3) + priority + category_bonus + min(s.get('related_count', 1), 5)*3, 2)

def feed_items():
    session = requests.Session()
    items, health = [], []
    for name, url, fallback in SOURCES:
        try:
            r = session.get(url, headers=UA, timeout=16)
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
            if not parsed.entries: raise ValueError('Feed returned no entries')
            accepted=0
            for entry in parsed.entries[:45]:
                link = (entry.get('link') or '').strip()
                title = clean(entry.get('title'), 170)
                if not link.startswith('https://') or len(title)<15: continue
                # Protect against malformed links and javascript URLs
                if urlparse(link).netloc == '': continue
                dt = published(entry)
                if dt < NOW-timedelta(days=7) or dt > NOW+timedelta(hours=2): continue
                summary = clean(entry.get('summary') or entry.get('description'), 220)
                if summary.lower().startswith(title.lower()[:40]): summary = ''
                eid = hashlib.sha256((name+'|'+link).encode()).hexdigest()[:18]
                items.append(dict(id=eid,title=title,description=summary,source=name,url=link,
                                  category=categorize(title,fallback),published=dt.isoformat().replace('+00:00','Z')))
                accepted+=1
            health.append({'source':name,'status':'ok','items':accepted})
        except Exception as exc:
            print(f'{name}: {type(exc).__name__}: {str(exc)[:120]}')
            health.append({'source':name,'status':'unavailable','items':0})
    return items, health

def group_stories(items):
    items.sort(key=lambda s:s['published'], reverse=True)
    groups=[]
    for item in items:
        words=signature(item['title'])
        duplicate=None
        if len(words)>=4:
            for group in groups:
                target=signature(group['title'])
                if len(words & target)>=4 and len(words & target)/max(1,len(words|target))>=.55:
                    duplicate=group
                    break
        if duplicate:
            if duplicate['source']!=item['source'] and item['url'] not in {x['url'] for x in duplicate['related']}:
                duplicate['related'].append({'source':item['source'],'url':item['url'],'title':item['title']})
            continue
        item['related']=[]
        groups.append(item)
    for item in groups:
        item['related_count']=1+len(item['related'])
        item['score']=score_story(item)
    return sorted(groups,key=lambda s:s['published'],reverse=True)

def daily_briefing(items, date):
    # Select consequential news from the last ~30 hours, favor different topics.
    recent=[x for x in items if datetime.fromisoformat(x['published'].replace('Z','+00:00'))>=NOW-timedelta(hours=30)]
    ranked=sorted(recent,key=lambda x:x['score'],reverse=True)
    selected=[]
    counts=Counter()
    for item in ranked:
        if len(selected)>=8: break
        if counts[item['category']]>=3: continue
        selected.append(item['id'])
        counts[item['category']]+=1
    return {'date':date,'generatedAt':NOW.isoformat().replace('+00:00','Z'), 'storyIds':selected,
            'editorialNote':'Automatically ranked by recency, topic signals and source coverage. This is not an AI-verified editorial selection.'}

def main():
    old = read_json(DATA/'news.json', {})
    incoming, health=feed_items()
    by_id={x['id']:x for x in old.get('stories',[]) if x.get('id') and x.get('published')}
    for item in incoming: by_id[item['id']]=item
    valid=[]
    for item in by_id.values():
        try:
            if datetime.fromisoformat(item['published'].replace('Z','+00:00'))>=NOW-timedelta(days=7):valid.append(item)
        except (KeyError,ValueError): pass
    stories=group_stories(valid)[:500]
    archive=read_json(DATA/'briefings.json',{'briefings':[]}).get('briefings',[])
    today=NOW.astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
    archive=[x for x in archive if x.get('date','')>= (NOW.astimezone(ZoneInfo('America/New_York'))-timedelta(days=6)).strftime('%Y-%m-%d')]
    if NOW.astimezone(ZoneInfo('America/New_York')).hour >= 6 and not any(x.get('date')==today for x in archive) and incoming:
        archive.append(daily_briefing(stories,today))
    archive=sorted(archive,key=lambda x:x['date'],reverse=True)[:7]
    result={'updatedAt':NOW.isoformat().replace('+00:00','Z') if incoming else old.get('updatedAt'),
            'attemptedAt':NOW.isoformat().replace('+00:00','Z'),
            'stories':stories,'sources':health, 'liveCount':len(incoming)}
    (DATA/'news.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (DATA/'briefings.json').write_text(json.dumps({'briefings':archive},ensure_ascii=False,indent=2)+'\n')
    print(f'Collected {len(incoming)} items; retained {len(stories)} stories; {len(archive)} briefings')

if __name__=='__main__':main()
