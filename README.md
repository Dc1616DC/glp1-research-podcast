# GLP-1 Research Podcast

Automated weekly podcast analyzing GLP-1 and obesity medication research from PubMed. Uses Claude for script generation and ElevenLabs for AI-generated audio.

## Features

- **Automated research fetching**: Pulls latest GLP-1 studies from PubMed RSS feeds every Monday
- **AI-generated scripts**: Claude creates conversational dialogue between two hosts
- **Realistic voices**: ElevenLabs generates audio with distinct voices for each host
- **Podcast RSS feed**: Valid podcast feed hosted on GitHub Pages
- **Completely hands-off**: Runs automatically via GitHub Actions

## Hosts

- **Dan**: Registered dietitian, evidence-focused, appropriately skeptical
- **Alex**: Science journalist, asks clarifying questions

## Setup Instructions

### Prerequisites

1. **Anthropic API Key**: Get one at [console.anthropic.com](https://console.anthropic.com)
2. **ElevenLabs API Key**: Get one at [elevenlabs.io](https://elevenlabs.io)

### Step 1: Create GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Repository name: `glp1-research-podcast`
3. Make it **Public** (required for GitHub Pages)
4. Do NOT initialize with README
5. Click "Create repository"

### Step 2: Push Code to GitHub

```bash
cd glp1-research-podcast
git init
git add .
git commit -m "Initial commit: GLP-1 Research Podcast automation"
git remote add origin https://github.com/YOUR_USERNAME/glp1-research-podcast.git
git branch -M main
git push -u origin main
```

### Step 3: Add API Keys as Secrets

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add two secrets:
   - Name: `ANTHROPIC_API_KEY`, Value: your Claude API key
   - Name: `ELEVENLABS_API_KEY`, Value: your ElevenLabs API key

### Step 4: Enable GitHub Pages

1. In repository Settings → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `/ (root)`
4. Click **Save**

### Step 5: Update GitHub Username

Edit `main.py` and replace `YOUR_GITHUB_USERNAME` with your actual GitHub username:

```python
GITHUB_USERNAME = "your-actual-username"  # Line 22
```

Commit and push the change:

```bash
git add main.py
git commit -m "Update GitHub username"
git push
```

### Step 6: Run Your First Episode

1. Go to **Actions** tab in your repository
2. Click **Weekly GLP-1 Research Podcast**
3. Click **Run workflow** → **Run workflow**
4. Wait 3-5 minutes for completion

### Step 7: Subscribe to Your Podcast

Your RSS feed URL:
```
https://YOUR_USERNAME.github.io/glp1-research-podcast/feed.xml
```

**Apple Podcasts:**
1. Library → Edit → Add a Show by URL
2. Paste your feed URL

**Other podcast apps:**
Use "Add by URL" or "Add RSS feed" option

## Schedule

The podcast automatically generates every Monday at:
- 12:00 UTC
- 8:00 AM EST
- 5:00 AM PST

## File Structure

```
glp1-research-podcast/
├── .github/
│   └── workflows/
│       └── weekly_podcast.yml   # GitHub Actions workflow
├── episodes/                     # Generated MP3 files
├── main.py                       # Main podcast generator
├── requirements.txt              # Python dependencies
├── feed.xml                      # Podcast RSS feed (auto-generated)
├── latest_script.txt             # Most recent script (for debugging)
└── README.md
```

## PubMed Search Queries

The system searches for research on:
- GLP-1 agonists AND muscle mass/protein intake
- Semaglutide OR tirzepatide AND nutrition
- GLP-1 AND side effects/nausea
- Anti-obesity medications AND protein

## Customization

### Adjust Episode Length

In `main.py`, modify the Claude prompt (line ~95):
- Current: "2000-2500 words (15-18 minutes)"
- Shorter: "1200-1500 words (8-10 minutes)"
- Longer: "3000-3500 words (20-25 minutes)"

### Change Voices

Update voice IDs in `main.py` (lines 29-30):
- Browse voices at [elevenlabs.io/voice-library](https://elevenlabs.io/voice-library)
- Get voice IDs from the voice details page

### Modify Search Topics

Edit `PUBMED_FEEDS` list in `main.py` (lines 23-27)

## Estimated Costs

- **Anthropic**: ~$0.30-0.50 per episode (Claude Sonnet)
- **ElevenLabs**:
  - Free tier: 10,000 characters/month (~2 short episodes)
  - Starter ($5/mo): 30,000 characters/month (~4-5 episodes)

## Troubleshooting

### No studies found
- PubMed RSS feeds may be temporarily unavailable
- Try running the workflow again

### Audio generation fails
- Check ElevenLabs API quota
- Verify API key is correct

### Feed validation errors
- Test feed at [podba.se/validate](https://podba.se/validate)
- Check XML syntax in feed.xml

### GitHub Actions fails
- Check the Actions log for error details
- Verify both API secrets are set correctly

## License

MIT License - Feel free to fork and customize for your own research topics!
