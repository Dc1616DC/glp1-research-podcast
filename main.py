#!/usr/bin/env python3
"""
Health Research Podcast Generator

Automated podcast analyzing health and nutrition research from PubMed.
Uses Claude for script generation and ElevenLabs for audio synthesis.
Supports multiple topic categories.
"""

import os
import re
import hashlib
import requests
import time
from datetime import datetime, timezone
from dateutil import parser as date_parser
from bs4 import BeautifulSoup
from anthropic import Anthropic
from elevenlabs import ElevenLabs
from pydub import AudioSegment
import xml.etree.ElementTree as ET
from xml.dom import minidom
import urllib.parse
import tempfile
import shutil

# Configuration
GITHUB_USERNAME = "Dc1616DC"
REPO_NAME = "glp1-research-podcast"

# Topic configurations
TOPICS = {
    "glp1": {
        "name": "GLP-1 Research Digest",
        "description": "GLP-1 and obesity medication research",
        "file_prefix": "glp1-digest",
        "queries": [
            '"GLP-1 agonist" AND ("muscle mass" OR "protein intake")',
            '("semaglutide" OR "tirzepatide") AND nutrition',
            '"GLP-1" AND ("side effects" OR "nausea")',
            '"Anti Obesity Medications" AND protein',
        ],
        "host_focus": """HOST 1 - DAN:
- Registered dietitian with 15 years of clinical experience
- Evidence-focused and appropriately skeptical
- Critical of poorly designed studies and overhyped findings
- Speaks in clear, accessible language but doesn't dumb things down
- Occasionally uses dry humor

HOST 2 - ALEX:
- Science journalist who covers metabolic health
- Asks the questions that listeners would ask
- Helps translate complex concepts
- Curious and engaged, but defers to Dan on clinical matters
- Good at drawing out practical implications""",
        "context": "GLP-1 and obesity medication research for healthcare professionals and educated patients"
    },
    "cardiovascular": {
        "name": "Heart Health Research Digest",
        "description": "Cardiovascular disease and nutrition research",
        "file_prefix": "heart-health",
        "queries": [
            '"cardiovascular disease" AND (diet OR nutrition)',
            '"heart disease" AND ("Mediterranean diet" OR "DASH diet")',
            '(hypertension OR "blood pressure") AND (sodium OR potassium OR diet)',
            '"atherosclerosis" AND (cholesterol OR "saturated fat" OR nutrition)',
            '"heart failure" AND (nutrition OR "dietary intervention")',
        ],
        "host_focus": """HOST 1 - DAN:
- Registered dietitian specializing in cardiac rehabilitation
- Evidence-focused and appropriately skeptical of fad diets
- Critical of poorly designed studies and supplement industry hype
- Speaks in clear, accessible language about complex lipid science
- Occasionally uses dry humor about butter and egg controversies

HOST 2 - ALEX:
- Science journalist who covers cardiovascular health
- Asks the questions that heart patients would ask
- Helps translate complex cholesterol and blood pressure concepts
- Curious and engaged, but defers to Dan on clinical nutrition
- Good at drawing out practical dietary implications""",
        "context": "cardiovascular and heart health research for healthcare professionals and health-conscious individuals"
    },
    "metabolic": {
        "name": "Metabolic Health Digest",
        "description": "Metabolism, diabetes, and nutrition research",
        "file_prefix": "metabolic-health",
        "queries": [
            '"type 2 diabetes" AND (nutrition OR diet OR "lifestyle intervention")',
            '"insulin resistance" AND (exercise OR diet OR fasting)',
            '"metabolic syndrome" AND (nutrition OR "weight loss")',
            '"glycemic control" AND (fiber OR "low carbohydrate" OR protein)',
            '"intermittent fasting" AND (metabolism OR "blood glucose")',
        ],
        "host_focus": """HOST 1 - DAN:
- Registered dietitian specializing in diabetes and metabolic health
- Evidence-focused and skeptical of metabolic quick-fixes
- Critical of poorly designed studies and keto/fasting hype
- Speaks in clear, accessible language about blood sugar science
- Occasionally uses dry humor about carb-phobia trends

HOST 2 - ALEX:
- Science journalist who covers metabolic health and longevity
- Asks the questions that pre-diabetics and health optimizers would ask
- Helps translate complex insulin and metabolism concepts
- Curious and engaged, but defers to Dan on clinical matters
- Good at drawing out practical lifestyle implications""",
        "context": "metabolic health, diabetes prevention, and nutrition research for healthcare professionals and health-conscious individuals"
    }
}

# E-utilities base URLs
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# ElevenLabs voice IDs
VOICE_DAN = "pNInz6obpgDQGcFmaJgB"  # Adam - male voice for Dan
VOICE_ALEX = "21m00Tcm4TlvDq8ikWAM"  # Rachel - female voice for Alex


def fetch_studies(queries, max_studies=5):
    """
    Fetch unique studies from PubMed using E-utilities API.
    Returns a list of dicts with title, abstract, link, and pubdate.
    """
    print("Fetching studies from PubMed...")

    all_pmids = set()

    # Step 1: Search for PMIDs from each query (with rate limiting)
    for i, query in enumerate(queries):
        try:
            # Rate limit: NCBI allows 3 requests/second without API key
            if i > 0:
                time.sleep(0.5)

            params = {
                'db': 'pubmed',
                'term': query,
                'retmax': 10,
                'sort': 'date',
                'retmode': 'json'
            }
            response = requests.get(ESEARCH_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            pmids = data.get('esearchresult', {}).get('idlist', [])
            all_pmids.update(pmids)
            print(f"  Query '{query[:40]}...' returned {len(pmids)} results")

        except Exception as e:
            print(f"Error searching PubMed for '{query[:30]}...': {e}")
            continue

    if not all_pmids:
        print("No PMIDs found from any query")
        return []

    # Step 2: Fetch article details for all PMIDs
    print(f"Fetching details for {len(all_pmids)} unique articles...")

    # Rate limit before fetching
    time.sleep(1)

    try:
        params = {
            'db': 'pubmed',
            'id': ','.join(all_pmids),
            'retmode': 'xml'
        }
        response = requests.get(EFETCH_URL, params=params, timeout=60)
        response.raise_for_status()

        # Parse XML response
        soup = BeautifulSoup(response.content, 'xml')
        articles = soup.find_all('PubmedArticle')

        all_studies = []
        for article in articles:
            try:
                # Extract title
                title_elem = article.find('ArticleTitle')
                title = title_elem.get_text() if title_elem else "No title"

                # Extract abstract
                abstract_elem = article.find('Abstract')
                if abstract_elem:
                    abstract_texts = abstract_elem.find_all('AbstractText')
                    abstract = ' '.join([t.get_text() for t in abstract_texts])
                else:
                    abstract = "No abstract available."

                # Extract PMID for link
                pmid_elem = article.find('PMID')
                pmid = pmid_elem.get_text() if pmid_elem else ""
                link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

                # Extract publication date
                pub_date_elem = article.find('PubDate')
                if pub_date_elem:
                    year = pub_date_elem.find('Year')
                    month = pub_date_elem.find('Month')
                    day = pub_date_elem.find('Day')

                    year_str = year.get_text() if year else "2024"
                    month_str = month.get_text() if month else "Jan"
                    day_str = day.get_text() if day else "1"

                    try:
                        parsed_date = date_parser.parse(f"{month_str} {day_str}, {year_str}")
                    except:
                        parsed_date = datetime.now(timezone.utc)
                else:
                    parsed_date = datetime.now(timezone.utc)

                study = {
                    'title': title,
                    'abstract': abstract,
                    'link': link,
                    'pubdate': parsed_date,
                }
                all_studies.append(study)

            except Exception as e:
                print(f"Error parsing article: {e}")
                continue

    except Exception as e:
        print(f"Error fetching article details: {e}")
        return []

    # Sort by publication date (most recent first) and limit
    all_studies.sort(key=lambda x: x['pubdate'], reverse=True)
    studies = all_studies[:max_studies]

    print(f"Found {len(studies)} unique studies")
    return studies


def analyze_with_claude(studies, topic_config):
    """
    Generate a conversational podcast script using Claude API.
    Returns the script text.
    """
    print("Generating podcast script with Claude...")

    client = Anthropic()

    # Format studies for the prompt
    studies_text = ""
    for i, study in enumerate(studies, 1):
        studies_text += f"""
STUDY {i}:
Title: {study['title']}
Abstract: {study['abstract']}
Link: {study['link']}
Published: {study['pubdate'].strftime('%Y-%m-%d')}
---
"""

    prompt = f"""You are writing a podcast script for "The {topic_config['name']}," a podcast that breaks down the latest {topic_config['context']}.

CREATE A CONVERSATIONAL SCRIPT BETWEEN TWO HOSTS:

{topic_config['host_focus']}

STUDIES TO COVER:
{studies_text}

SCRIPT REQUIREMENTS:
1. LENGTH: 2000-2500 words (approximately 15-18 minutes of audio)
2. FORMAT: Use "Dan:" and "Alex:" labels for each speaker turn
3. STRUCTURE:
   - Brief intro/welcome (30 seconds)
   - Cover each study: what they did, methodology critique, patient implications
   - Dan should be critical of weak methodologies (small sample sizes, short duration, industry funding bias)
   - Alex asks clarifying questions listeners would want answered
   - End with key takeaways

4. TONE:
   - Professional but conversational
   - Natural dialogue with some back-and-forth
   - Include brief reactions ("That's interesting..." "Right, and...")
   - Avoid sounding scripted or robotic

5. CONTENT GUIDELINES:
   - Be specific about numbers (sample sizes, effect sizes, p-values when relevant)
   - Discuss clinical relevance, not just statistical significance
   - Note limitations honestly
   - Provide actionable insights for practitioners and patients

Write the complete script now. Start directly with the dialogue (no meta-commentary)."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    script = response.content[0].text

    # Save script for debugging
    with open("latest_script.txt", "w") as f:
        f.write(script)

    print(f"Script generated: {len(script)} characters")
    return script


def parse_script(script):
    """
    Parse the script into speaker segments.
    Returns a list of (speaker, text) tuples.
    """
    segments = []

    # Pattern to match speaker labels
    pattern = r'(Dan|Alex):\s*'

    # Split by speaker
    parts = re.split(pattern, script)

    # First part might be empty or intro text, skip it
    i = 1 if parts[0].strip() == '' or parts[0].strip() not in ['Dan', 'Alex'] else 0

    while i < len(parts) - 1:
        speaker = parts[i].strip()
        if speaker in ['Dan', 'Alex']:
            text = parts[i + 1].strip()
            if text:
                segments.append((speaker, text))
            i += 2
        else:
            i += 1

    return segments


def generate_conversational_audio(script, output_path="episode.mp3"):
    """
    Parse script and generate audio with ElevenLabs using two voices.
    Combines segments into a single MP3 file.
    """
    print("Generating audio with ElevenLabs...")

    client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))

    segments = parse_script(script)

    if not segments:
        raise ValueError("No valid speaker segments found in script")

    print(f"Found {len(segments)} speaker segments")

    # Create temp directory for audio segments
    temp_dir = tempfile.mkdtemp()
    audio_files = []

    try:
        for i, (speaker, text) in enumerate(segments):
            print(f"Generating segment {i+1}/{len(segments)} ({speaker})...")

            voice_id = VOICE_DAN if speaker == "Dan" else VOICE_ALEX

            # Generate audio
            audio_generator = client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id="eleven_monolingual_v1",
                voice_settings={
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            )

            # Save segment
            segment_path = os.path.join(temp_dir, f"segment_{i:04d}.mp3")
            with open(segment_path, "wb") as f:
                for chunk in audio_generator:
                    f.write(chunk)

            audio_files.append(segment_path)

        print("Combining audio segments...")

        # Combine all segments
        combined = AudioSegment.empty()

        for audio_file in audio_files:
            segment = AudioSegment.from_mp3(audio_file)
            # Add small pause between speakers (300ms)
            combined += segment + AudioSegment.silent(duration=300)

        # Export combined audio
        combined.export(output_path, format="mp3", bitrate="128k")

        # Get duration
        duration_seconds = len(combined) / 1000
        print(f"Audio generated: {output_path} ({duration_seconds:.1f} seconds)")

        return output_path, duration_seconds

    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir)


def update_rss_feed(episode_title, episode_description, mp3_filename, duration_seconds):
    """
    Create or update the podcast RSS feed.
    """
    print("Updating RSS feed...")

    feed_path = "feed.xml"
    base_url = f"https://{GITHUB_USERNAME}.github.io/{REPO_NAME}"
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{REPO_NAME}/main"

    # iTunes namespace
    itunes_ns = "http://www.itunes.com/dtds/podcast-1.0.dtd"

    # Check if feed exists
    if os.path.exists(feed_path):
        tree = ET.parse(feed_path)
        root = tree.getroot()
        channel = root.find('channel')
    else:
        # Create new feed
        root = ET.Element('rss')
        root.set('version', '2.0')
        root.set('xmlns:itunes', itunes_ns)
        root.set('xmlns:content', 'http://purl.org/rss/1.0/modules/content/')

        channel = ET.SubElement(root, 'channel')

        # Channel metadata
        ET.SubElement(channel, 'title').text = "Health Research Digest"
        ET.SubElement(channel, 'link').text = base_url
        ET.SubElement(channel, 'description').text = "Weekly analysis of the latest health and nutrition research. Covering GLP-1 medications, cardiovascular health, and metabolic research. Hosted by Dan (registered dietitian) and Alex (science journalist)."
        ET.SubElement(channel, 'language').text = "en-us"
        ET.SubElement(channel, 'lastBuildDate').text = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')

        # iTunes tags
        itunes_author = ET.SubElement(channel, '{%s}author' % itunes_ns)
        itunes_author.text = "Health Research Digest"

        itunes_summary = ET.SubElement(channel, '{%s}summary' % itunes_ns)
        itunes_summary.text = "Weekly analysis of the latest health and nutrition research for healthcare professionals and informed patients."

        itunes_explicit = ET.SubElement(channel, '{%s}explicit' % itunes_ns)
        itunes_explicit.text = "no"

        itunes_category = ET.SubElement(channel, '{%s}category' % itunes_ns)
        itunes_category.set('text', 'Health & Fitness')

        itunes_subcategory = ET.SubElement(itunes_category, '{%s}category' % itunes_ns)
        itunes_subcategory.set('text', 'Nutrition')

        tree = ET.ElementTree(root)

    # Update lastBuildDate
    last_build = channel.find('lastBuildDate')
    if last_build is not None:
        last_build.text = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')

    # Create new episode item
    item = ET.Element('item')

    ET.SubElement(item, 'title').text = episode_title
    ET.SubElement(item, 'description').text = episode_description

    pub_date = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
    ET.SubElement(item, 'pubDate').text = pub_date

    # GUID
    guid = ET.SubElement(item, 'guid')
    guid.set('isPermaLink', 'false')
    guid.text = f"{REPO_NAME}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Enclosure (the MP3 file)
    enclosure = ET.SubElement(item, 'enclosure')
    enclosure.set('url', f"{raw_url}/episodes/{mp3_filename}")
    enclosure.set('type', 'audio/mpeg')
    # Get file size
    mp3_path = f"episodes/{mp3_filename}"
    if os.path.exists(mp3_path):
        enclosure.set('length', str(os.path.getsize(mp3_path)))
    else:
        enclosure.set('length', '0')

    # iTunes episode tags
    itunes_duration = ET.SubElement(item, '{%s}duration' % itunes_ns)
    minutes = int(duration_seconds // 60)
    seconds = int(duration_seconds % 60)
    itunes_duration.text = f"{minutes}:{seconds:02d}"

    itunes_summary = ET.SubElement(item, '{%s}summary' % itunes_ns)
    itunes_summary.text = episode_description

    itunes_explicit = ET.SubElement(item, '{%s}explicit' % itunes_ns)
    itunes_explicit.text = "no"

    # Insert new item at the beginning of the channel (after channel metadata)
    items = channel.findall('item')
    if items:
        # Insert before first item
        channel.insert(list(channel).index(items[0]), item)
    else:
        channel.append(item)

    # Pretty print XML
    xml_string = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent="  ")

    # Remove extra blank lines
    pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])

    # Write feed
    with open(feed_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)

    print(f"RSS feed updated: {feed_path}")


def main():
    """
    Main pipeline: fetch studies, generate script, create audio, update feed.
    """
    # Get topic from environment variable, default to glp1
    topic_key = os.environ.get("PODCAST_TOPIC", "glp1").lower()

    if topic_key not in TOPICS:
        print(f"Unknown topic: {topic_key}. Available topics: {list(TOPICS.keys())}")
        print("Defaulting to 'glp1'")
        topic_key = "glp1"

    topic_config = TOPICS[topic_key]

    print("=" * 60)
    print(f"Health Research Podcast Generator")
    print(f"Topic: {topic_config['name']}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Step 1: Fetch studies
    studies = fetch_studies(topic_config['queries'], max_studies=5)

    if not studies:
        print("No studies found. Exiting.")
        return

    # Step 2: Generate script with Claude
    script = analyze_with_claude(studies, topic_config)

    # Step 3: Generate audio
    date_str = datetime.now().strftime('%Y-%m-%d')
    mp3_filename = f"{topic_config['file_prefix']}-{date_str}.mp3"
    mp3_path = f"episodes/{mp3_filename}"

    # Ensure episodes directory exists
    os.makedirs("episodes", exist_ok=True)

    audio_path, duration = generate_conversational_audio(script, mp3_path)

    # Step 4: Update RSS feed
    episode_title = f"{topic_config['name']} - {date_str}"

    # Create description from study titles
    study_titles = [s['title'][:100] for s in studies]
    episode_description = f"This episode covers: {'; '.join(study_titles)}"

    update_rss_feed(episode_title, episode_description, mp3_filename, duration)

    print("=" * 60)
    print("Podcast generation complete!")
    print(f"Episode: {mp3_path}")
    print(f"Duration: {duration/60:.1f} minutes")
    print("=" * 60)


if __name__ == "__main__":
    main()
