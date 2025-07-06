# Hashnode to Obsidian Converter

**A one-time migration tool** for converting Hashnode blog exports to Obsidian-compatible format with optional API enrichment and image downloading. Just add your Hashnode export JSON to the project folder and run the h2o.py script, then open the folder with Obsidian to see all your notes working locally with images downloaded from the CDN. 

## 🎯 Purpose
This tool is designed for **one-time migration** from Hashnode to Obsidian. It processes your Hashnode JSON export and creates:
- Clean Obsidian markdown files with proper YAML frontmatter
- Migration-ready folder structure (also compatible with 11ty)
- Local image downloads (optional)
- Enriched tag names via Hashnode API (optional)

## Why Obsidian? 
There are plenty of Markdown-based static site generators that the Hashnode data could be exported to, so why choose Obsidian? None of the free solutions provide the blog authoring tools, Markdown editing with drag-and-drop images, image hosting, etc. You would have to go host images somewhere else first, then reference them in your Markdown.

Obsidian privides an excellent writing experience with drag-and-drop images, and a slick interface for editing YML properties for SEO and CMS fields. Once posts written in Obsidian are ready to publish, there are a wide range of free and paid tools to publish notes as a web page, or you can build your own solution to push content to any other platform. 
![Screenshot 2025-07-06 at 12 14 06 PM](https://github.com/user-attachments/assets/bfc18495-fd4d-4023-8781-641ef8fcbed1)


In other words, this solution prioritizes replacing the Hashnode *writing experience*, and leaves it up to you to choose where to host next, and how to convert to the right format. For my blog, I'll be using 11ty, and writing a seprate tool to import from Obsidian. 


## ⚡ Quick Start
1. **Clone repository**
   ```bash
   git clone https://github.com/GreenFlux/hashnode-to-obsidian.git
   cd hashnode-to-obsidian
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Get Hashnode export**
   - Go to Hashnode Dashboard > Settings > Export
   - Download "Export all articles" JSON file
   - Place in project directory as `hashnode-export.json`

5. **Set up API key** (optional but recommended)
   ```bash
   cp .env.example .env
   # Edit .env and add your Hashnode API key from https://hashnode.com/settings/developer
   ```

6. **Test run** (recommended first step)
   ```bash
   python h2o.py hashnode-export.json --limit 2 --skip-images --dry-run
   ```

7. **Full conversion**
   ```bash
   python h2o.py hashnode-export.json --output ./my-obsidian-vault
   ```

## ✨ Features
- ✅ **One-time migration tool** - Convert your entire Hashnode blog
- ✅ **Optional API enrichment** - Get readable tag names (vs IDs)
- ✅ **Optional image downloading** - Store images locally with proper paths
- ✅ **Obsidian-compatible** - Proper YAML frontmatter and markdown structure
- ✅ **Migration-ready** - Folder structure works for future 11ty migration
- ✅ **Draft handling** - Separates drafts from published posts
- ✅ **Clean YAML** - Handles multiline descriptions with literal block scalars

## 📋 Command Reference
```bash
python h2o.py EXPORT_FILE [OPTIONS]

Options:
  --output, -o PATH       Output directory (default: ./obsidian-vault)
  --limit, -l N          Test with N posts only (great for testing)
  --skip-images          Skip image downloads (uses remote URLs)
  --skip-enrichment      Skip API calls (tags show as IDs)
  --dry-run              Preview without writing files
  --verbose, -v          Enable detailed output
```

## 🚀 Usage Examples
```bash
# Test with 2 posts, no images, preview only
python h2o.py hashnode-export.json --limit 2 --skip-images --dry-run

# Quick migration without API enrichment (offline mode)
python h2o.py hashnode-export.json --skip-enrichment --output ./my-vault

# Full migration with all features (recommended)
python h2o.py hashnode-export.json --output ./my-obsidian-vault

# Large export testing (start small)
python h2o.py hashnode-export.json --limit 5 --skip-images
```

## 📁 Output Structure
```
my-obsidian-vault/
├── drafts/                    # Draft posts
├── templates/                 # Obsidian templates
│   └── Post Template.md       # Blank YAML template
├── posts/                     # Published posts (flat structure for 11ty compatibility)
│   ├── my-first-post.md
│   └── another-post.md
└── images/                    # Images organized by post
    └── posts/
        ├── my-first-post/
        │   ├── cover.jpg
        │   └── image-1.png
        └── another-post/
            └── cover.jpg
```

## 🛠️ Troubleshooting
- **Missing API key**: Use `--skip-enrichment` flag (tags will show as IDs like "Tag-abc123")
- **Large exports**: Use `--limit N` for testing first (e.g., `--limit 5`)
- **Network issues**: Use `--skip-images` flag (keeps remote Hashnode URLs)
- **API errors**: Converter automatically falls back to local data
- **Memory issues**: Process in smaller batches using `--limit`

## 🔧 Technical Details
- **Language**: Python 3.8+
- **Dependencies**: See `requirements.txt`
- **Image formats**: Supports jpg, png, gif, webp, svg
- **API**: Optional Hashnode GraphQL API for tag enrichment
- **Output**: Obsidian-compatible markdown with YAML frontmatter

## 📝 Notes
- This is a **one-time migration tool**, not a sync tool
- API enrichment is **optional** but highly recommended for better tag names
- Image downloading is **optional** but removes dependency on Hashnode CDN
- Generated structure is compatible with both Obsidian and 11ty static site generators
