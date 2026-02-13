import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime
import json
import re
import ssl
import urllib3
import os
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from dotenv import load_dotenv

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

# ================= Configuration =================
MAIN_PAGE_URL = "https://kpopofficial.com/kpop-comebacks/"
OUTPUT_JSON = "kpop_schedule_dataset.json"
BANNER_JSON = "kpop_banner_data.json"
OUTPUT_MD = "kpop_upcoming_report_v2.md"
CURRENT_DATE = datetime.now()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

# ================= AI Setup =================
try:
    from openai import OpenAI
    openai_client = None
except ImportError:
    OpenAI = None
    openai_client = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OpenAI and OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"⚠️ OpenAI Init Error: {e}")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if genai and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ================= Network =================
class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx
        )

session = requests.Session()
session.mount("https://", TLSAdapter())

def get_soup(url):
    try:
        time.sleep(random.uniform(1.0, 2.0))
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": "https://kpopofficial.com/",
            "Upgrade-Insecure-Requests": "1",
        }
        response = session.get(url, headers=headers, timeout=20, verify=True)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        elif response.status_code in [403, 429]:
            time.sleep(5)
            response = session.get(url, headers=headers, timeout=20, verify=True)
            if response.status_code == 200:
                return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"   ❌ Request Error: {e}")
    return None

# ================= Discovery & Extraction =================
def auto_discover_monthly_urls():
    print(f"🕵️ Finding monthly schedule pages from {MAIN_PAGE_URL}...")
    soup = get_soup(MAIN_PAGE_URL)
    if not soup: return []

    discovered_urls = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if "kpop-comeback-schedule-" in href:
             discovered_urls.add(href)
    
    sorted_urls = sorted(list(discovered_urls))
    print(f"✅ Found {len(sorted_urls)} monthly pages.")
    return sorted_urls

def extract_raw_events_from_month(url):
    soup = get_soup(url)
    if not soup: return []
    
    events = []
    items = soup.select('li.gspbgrid_item')
    if items:
        for item in items:
            link_tag = item.select_one('a.gspbgrid_item_link') or item.find('a', href=True)
            if not link_tag: continue
            
            href = link_tag['href']
            if '/album/' not in href and '/event/' not in href: continue
            
            title = link_tag.get('title', '').strip()
            if not title:
                title = link_tag.get_text(strip=True)
            
            date_text = "TBA"
            meta_spans = item.select('.gspb_meta_value')
            for span in meta_spans:
                text = span.get_text(strip=True)
                if any(m in text for m in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]) or "Coming Soon" in text:
                    date_text = text
                    break
            
            events.append({
                "title": title,
                "link": href,
                "date_text": date_text
            })
            
    # Fallback for legacy layout
    if not events:
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/album/' in href or '/event/' in href:
                title = a.get_text(strip=True)
                if not title: continue
                events.append({
                    "title": title,
                    "link": href,
                    "date_text": "Unknown"
                })
    return events

# ================= AI Filtering =================
def ai_filter_candidates(events):
    """
    Uses AI to filter the list of events, keeping only those happening today or in the future.
    """
    if not events: return []
    
    print(f"\n🧠 AI Filtering {len(events)} candidates...")
    if openai_client:
        print("   ✅ OpenAI Client is available.")
    else:
        print("   ❌ OpenAI Client is NOT available.")

    # Prepare prompt
    today_str = CURRENT_DATE.strftime('%B %d, %Y')
    
    # Batch processing to avoid token limits (50 items per batch)
    filtered_results = []
    batch_size = 50
    
    for i in range(0, len(events), batch_size):
        batch = events[i:i+batch_size]
        print(f"   -> Processing batch {i//batch_size + 1}...")
        
        prompt = f"""
        Current Date: {today_str}
        
        Task: Filter the following K-Pop events.
        Keep items ONLY if:
        1. The date indicates TODAY or FUTURE relative to {today_str}.
        2. The date is "TBA", "Coming Soon", or ambiguous (e.g. just "February 2026" if we are in early Feb).
        3. EXCLUDE items that have clearly passed (e.g. yesterday or last month).
        
        Input List (JSON):
        {json.dumps(batch, ensure_ascii=False)}
        
        Return ONLY a JSON array of the kept items. Do not change the item structure.
        """
        
        response_text = ""
        
        # Try Gemini first
        if genai:
            try:
                # Use available model
                model = genai.GenerativeModel('models/gemini-3-flash-preview')
                response = model.generate_content(prompt)
                response_text = response.text
                if "json" in response_text:
                    match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                    if match:
                        response_text = match.group(1)
            except Exception as e:
                print(f"      Running Gemini failed: {e}")
        
        # Fallback to OpenAI
        if not response_text and openai_client:
            try:
                print("      Attempting OpenAI fallback...")
                completion = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                response_text = completion.choices[0].message.content
            except Exception as e:
                print(f"      Running OpenAI failed: {e}")

        # Parse JSON
        try:
            if not response_text: raise ValueError("No response from AI")
            kept_items = json.loads(response_text)
            filtered_results.extend(kept_items)
            print(f"      Batch filtered: {len(batch)} -> {len(kept_items)}")
        except Exception as e:
            print(f"      ⚠️ Failed to parse AI response: {e}. Keeping original batch safely.")
            filtered_results.extend(batch)
            
    print(f"✅ AI Filtered: {len(events)} -> {len(filtered_results)} items.")
    return filtered_results

# ================= Detail Scraping & Output =================
def parse_date(date_str):
    if not date_str: return None
    clean_str = date_str.replace('\n', ' ')
    clean_str = re.sub(r'(\d{1,2}:\d{2}\s?(?:AM|PM|KST).*)|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|·', '', clean_str, flags=re.IGNORECASE).strip()
    
    formats = ["%B %d, %Y", "%B %Y", "%Y-%m-%d", "%B %d %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(clean_str, fmt)
        except ValueError:
            continue
    return datetime(2099, 12, 31) # Default future date

def scrape_details(url):
    soup = get_soup(url)
    if not soup: return None

    data = {
        "Artist": "Unknown",
        "Album": "Unknown",
        "Release Date": "TBA",
        "Official Source": "None",
        "Source_URL": url,
        "Poster": "",
        "Tracklist": "TBA", 
        "sort_date": datetime(2099, 12, 31)
    }

    img_tag = soup.select_one('figure.wp-block-image img')
    if img_tag: data['Poster'] = img_tag.get('src')

    table = soup.select_one('figure.wp-block-table table')
    if table:
        for row in table.select('tr'):
            cols = row.select('td')
            if len(cols) == 2:
                key = cols[0].get_text(strip=True).replace(':', '')
                val_cell = cols[1]
                
                if "Source" in key or "Buy" in key:
                    text_content = val_cell.get_text(" ", strip=True)
                    for a in val_cell.find_all('a', href=True):
                        link_text = a.get_text(strip=True)
                        link_url = a['href']
                        text_content = text_content.replace(link_text, f"[{link_text}]({link_url})")
                    value = text_content
                else:
                    for br in val_cell.find_all('br'): br.replace_with('\n')
                    value = val_cell.get_text("\n", strip=True)

                data[key] = value

    if data['Artist'] == "Unknown":
        h1 = soup.select_one('h1')
        if h1:
            title_text = h1.get_text(strip=True)
            if '–' in title_text:
                parts = title_text.split('–', 1)
                data['Artist'] = parts[0].strip()
                data['Album'] = parts[1].strip()
            else:
                data['Artist'] = title_text

    date_str = data.get('Release Date', '')
    parsed = parse_date(date_str)
    if parsed: data['sort_date'] = parsed
    
    # Tracklist normalization
    for k, v in data.items():
        if 'Track' in k and k != 'Tracklist':
            data['Tracklist'] = v

    return data

def main():
    print(f"📅 System Date: {CURRENT_DATE.strftime('%Y-%m-%d')}")
    print("==================================================")
    
    # 1. Discover
    monthly_urls = auto_discover_monthly_urls()
    
    # 2. Extract Candidates
    raw_events = []
    print("\n🔍 Extracting raw candidates...")
    for url in monthly_urls:
         print(f"   -> {url}")
         raw_events.extend(extract_raw_events_from_month(url))
    
    # Deduplicate
    unique = {}
    for e in raw_events: unique[e['link']] = e
    raw_events = list(unique.values())
    
    # 3. AI Filter
    # Pass date info carefully
    filtered_events = ai_filter_candidates(raw_events)
    
    # 4. Scrape Details
    results = []
    print(f"\n🚀 Scraping details for {len(filtered_events)} events...")
    for i, e in enumerate(filtered_events):
        print(f"[{i+1}/{len(filtered_events)}] {e['title']}...", end="")
        res = scrape_details(e['link'])
        if res:
            print(" ✅")
            results.append(res)
        else:
            print(" ❌")
            
    results.sort(key=lambda x: x['sort_date'])
    
    # 5. Output
    # Full Dataset
    output_data = [{k: v for k, v in r.items() if k != 'sort_date'} for r in results]
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    # Banner Data
    banner_data = []
    for r in results:
        ts = int(r['sort_date'].timestamp() * 1000)
        s = r['sort_date'].strftime("%m.%d")
        clean_artist = r.get('Artist', 'Unknown').replace('\n', ' ').strip()
        clean_album = r.get('Album', 'Unknown').replace('\n', ' ').replace('View Details Album', '').strip()
        banner_data.append({"a": clean_artist, "l": clean_album, "ts": ts, "s": s})
        
    with open(BANNER_JSON, 'w', encoding='utf-8') as f:
        json.dump(banner_data, f, separators=(',', ':'), ensure_ascii=False)
        
    # Markdown Report
    with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
        f.write(f"# K-Pop Schedule (Generated {CURRENT_DATE.strftime('%Y-%m-%d')})\n\n")
        
        for item in results:
            artist = item.get('Artist', 'Unknown')
            album = item.get('Album', 'Unknown')
            date = item.get('Release Date', 'TBA')
            poster = item.get('Poster', '')
            source = item.get('Official Source', '')
            link = item.get('Source_URL', '')
            tracklist = item.get('Tracklist', 'TBA')

            f.write(f"## {artist}\n\n")
            if poster: f.write(f"![Poster]({poster})\n\n")
            f.write(f"- **Album**: {album}\n")
            f.write(f"- **Date**: {date}\n")
            f.write(f"- **Tracklist**: \n{tracklist}\n")
            f.write(f"- **Source**: {source}\n")
            f.write(f"- **Link**: [Detail Page]({link})\n")
            f.write("\n---\n\n")

    print(f"\n🎉 Skill Execution Complete!")
    print(f"1. {OUTPUT_JSON}")
    print(f"2. {BANNER_JSON}")
    print(f"3. {OUTPUT_MD}")

if __name__ == "__main__":
    main()
