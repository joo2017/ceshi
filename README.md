# 🎵 K-Pop Data Scraper Skill

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An automated AI-powered tool to scrape, filter, and organize K-Pop comeback schedules from [kpopofficial.com](https://kpopofficial.com). 

Features **Gemini 3 Flash** integration to intelligently filter out past events and keep your schedule up-to-date.

## ✨ Features

- **Auto-Discovery**: Automatically finds monthly schedule pages.
- **AI-Powered Filtering**: Uses Google Gemini (or OpenAI) to understand natural language dates and filter out expired events.
- **Rich Data**: Extracts Artist, Album, Release Date, Tracklist, and Official Source links.
- **Multi-Format Output**: Generates:
  - `kpop_schedule_dataset.json` (Structured Data)
  - `kpop_upcoming_report_v2.md` (Readable Report)
  - `kpop_banner_data.json` (For web components)

## 🚀 Installation

### 1. Clone or Download
Clone this repository to your local machine (or your AI agent's skill directory).

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys
Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
# Optional fallback
OPENAI_API_KEY=your_openai_api_key_here
```

## 🛠 Usage

Run the main script directly:

```bash
python kpop_skill_runner.py
```

The script will:
1. Scan for schedule pages.
2. Filter candidates using AI.
3. Scrape details for future events.
4. Generate output files in the current directory.

## 🤖 AI Model Support

- **Primary**: `models/gemini-3-flash-preview` (Fast & cost-effective)
- **Fallback**: `gpt-3.5-turbo` (If enabled)

## 📄 Output Examples

**JSON Data**:
```json
[
  {
    "Artist": "ITZY",
    "Album": "GOLD",
    "Release Date": "October 15, 2025",
    "Tracklist": "..."
  }
]
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
