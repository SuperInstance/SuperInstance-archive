# Search Guide

Master ActiveLog's powerful search capabilities to find any file instantly using AI-powered search, advanced filters, and intelligent suggestions.

## Search Basics

### Quick Search

The search bar is your gateway to finding anything:

**Location**: Top of every page
**Shortcut**: `Ctrl/Cmd + K` (opens focused search)
**Placeholder**: "Search files, folders, content..."

![Screenshot Placeholder: Search bar with cursor]

**Basic Search Examples**:
```
contract
vacation photos
meeting notes
```

### Search as You Type

ActiveLog provides instant results:
- Results appear as you type (after 2+ characters)
- Top matches shown immediately
- Full results page available via Enter
- Recent searches suggested

![Screenshot Placeholder: Search dropdown with suggestions]

### Search Scope

By default, search includes:
- 📄 **File names** - Exact and partial matches
- 📝 **File content** - Text inside documents
- 🏷️ **Tags and metadata** - Custom and AI-generated
- 💬 **Comments** - Collaboration discussions
- 📁 **Folder names** - Organization structure

## Search Operators

### Text Operators

**Exact Phrases**
```
"quarterly report" - Exact phrase match
"john smith" - Find exact name
```

**Boolean Logic**
```
contract AND signed - Both terms must exist
PDF OR document - Either term can exist  
report NOT draft - Include first, exclude second
```

**Wildcards**
```
report* - Matches report, reports, reporting
*2024 - Matches anything ending in 2024
proj?ct - Matches project or project (? = single character)
```

![Screenshot Placeholder: Search with operators showing results]

### Field-Specific Search

**Search Specific Fields**
```
title:budget - Search only in file titles
author:"john doe" - Search by author field
content:machine learning - Search file content only
tags:work - Search only in tags
```

**Available Fields**:
- `title:` - File/folder names
- `content:` - Text inside files  
- `author:` - File creator/author
- `tags:` - Assigned tags
- `type:` - File type/extension
- `size:` - File size
- `date:` - Creation/modification date
- `folder:` - Parent folder name

### Date and Time Search

**Relative Dates**
```
date:today - Files from today
date:yesterday - Files from yesterday
date:this week - Current week
date:last month - Previous month
date:this year - Current year
```

**Specific Date Ranges**
```
date:2024-01-01 - Specific date
date:>2024-01-01 - After specific date
date:2024-01-01..2024-12-31 - Date range
modified:last 7 days - Modified recently
```

**Time-Based Examples**
```
created:today AND type:pdf
modified:last week AND author:me
date:>2024-06-01 AND tags:project
```

![Screenshot Placeholder: Date picker in advanced search]

### Size and Type Filters

**File Sizes**
```
size:>10MB - Files larger than 10MB
size:<1KB - Files smaller than 1KB  
size:1MB..100MB - Size range
large - Shortcut for files >50MB
small - Shortcut for files <1MB
```

**File Types**
```
type:pdf - PDF files only
type:image - All image files
type:video - All video files
type:document - All document types
extension:docx - Specific extension
```

**Predefined Type Groups**:
- `documents` - PDF, DOC, TXT, etc.
- `images` - JPG, PNG, GIF, etc.
- `videos` - MP4, AVI, MOV, etc.
- `audio` - MP3, WAV, FLAC, etc.
- `archives` - ZIP, RAR, 7Z, etc.
- `code` - JS, PY, HTML, etc.

## Advanced Search Interface

### Advanced Search Form

Access via search dropdown or `Ctrl/Cmd + Shift + K`:

![Screenshot Placeholder: Advanced search form with all fields]

**Fields Available**:
1. **Keywords** - Main search terms
2. **File Types** - Checkboxes for common types
3. **Date Range** - Calendar picker
4. **Size Range** - Slider or input fields
5. **Tags** - Multi-select dropdown
6. **Folders** - Folder tree selector
7. **Authors** - People who created/modified
8. **Shared Status** - Private, shared, public

### Search Filters Sidebar

When viewing results, use the sidebar to refine:

**Filter Categories**:
- 📁 **Folders** - Narrow by location
- 📅 **Date Modified** - Time ranges
- 👤 **People** - Authors and editors
- 🏷️ **Tags** - All available tags
- 📄 **File Types** - By extension
- 💾 **File Size** - Size buckets
- 🔒 **Access Level** - Sharing permissions

**Dynamic Filters**:
Filters adapt based on your results. Only relevant options are shown.

![Screenshot Placeholder: Search results with filters sidebar]

## Smart Search Features

### AI-Powered Search

ActiveLog understands context and intent:

**Natural Language Queries**:
```
"presentations about AI from last month"
"photos from my vacation in Hawaii" 
"contracts that need to be signed"
"large video files taking up space"
```

**Concept Search**:
```
machine learning - Finds ML, artificial intelligence, neural networks
financial - Finds budget, revenue, accounting, finance
legal - Finds contracts, agreements, compliance
```

### Semantic Search

Find files by meaning, not just keywords:

**Examples**:
- Search "dog" → finds "puppy", "canine", "pet" files
- Search "car" → finds "vehicle", "automobile", "truck" files  
- Search "happy" → finds "joyful", "excited", "celebration" content

**How It Works**:
1. AI analyzes file content and context
2. Creates semantic embeddings (meaning vectors)
3. Matches your query intent to file meanings
4. Ranks results by semantic similarity

![Screenshot Placeholder: Semantic search results showing conceptual matches]

### Visual Similarity

Find images and documents that look similar:

**Access Methods**:
1. Right-click image → "Find Similar"
2. Search: `similar:image_name.jpg`
3. Use visual search in mobile app (camera icon)

**What It Finds**:
- Similar photos (same person, place, object)
- Documents with similar layouts
- Charts and graphs with similar patterns
- Screenshots of similar interfaces

### Auto-Complete and Suggestions

**Smart Suggestions**:
- Recent searches appear first
- Popular searches in your organization
- AI-suggested refinements
- Typo corrections and alternatives

**Query Enhancement**:
ActiveLog automatically suggests improvements:
```
Your search: "finacial report"
Suggested: "financial report" (typo correction)
Also try: "quarterly financial report" (enhancement)
```

## Search Results

### Results Layout

**Grid View** (Default)
- Thumbnail previews
- File names and types
- Relevance scores
- Quick actions overlay

**List View**  
- Detailed file information
- Modification dates and sizes
- Author information
- Path breadcrumbs

**Timeline View**
- Chronological organization
- Grouped by time periods
- Great for date-based searches

![Screenshot Placeholder: Different search result views]

### Result Ranking

Results are ranked by:

1. **Relevance Score** (0-100%)
   - Keyword match strength
   - Content relevance
   - User interaction history
   
2. **Recency Boost**
   - Recently accessed files rank higher
   - Configurable time decay
   
3. **Personal Relevance**
   - Your files rank higher than shared
   - Files you've interacted with boost up

### Search Highlighting

Found terms are highlighted in:
- File names and paths
- Content previews  
- Metadata fields
- Comments and descriptions

**Snippet Previews**:
See context around found terms:
```
...the quarterly financial report shows a 15% 
increase in revenue compared to last quarter...
```

## Saved Searches

### Creating Saved Searches

1. Perform a search with desired parameters
2. Click **"Save Search"** in results toolbar
3. Name your search (e.g., "Q4 Reports")
4. Choose to make it private or shared
5. Access from sidebar "Saved Searches"

![Screenshot Placeholder: Save search dialog]

### Smart Search Alerts

Get notified when new files match your searches:

1. Save a search as described above
2. Click **"Create Alert"** 
3. Choose notification method:
   - Email digest (daily/weekly)
   - Push notifications (immediate)
   - In-app notifications
4. Set alert conditions and frequency

**Alert Examples**:
- "New contracts uploaded" 
- "Large files added to project folder"
- "Photos tagged with 'vacation'"

### Search History

**Access Recent Searches**:
- Click search bar → see recent searches
- Settings → Privacy → Search History
- Clear history anytime for privacy

**Search Analytics**:
Premium users get search insights:
- Most common search terms
- Search success rates
- Time spent searching vs. finding

## Search Shortcuts and Quick Actions

### Keyboard Shortcuts

| Shortcut | Action |
|----------|---------|
| `Ctrl/Cmd + K` | Open search |
| `Ctrl/Cmd + Shift + K` | Advanced search |
| `Escape` | Close search |
| `↑/↓ Arrows` | Navigate results |
| `Enter` | Open selected result |
| `Ctrl/Cmd + Enter` | Open in new tab |

### Quick Search Prefixes

Type these prefixes for instant filtering:

| Prefix | Result |
|--------|--------|
| `@` | Search by attributes (@today, @images) |
| `#` | Search by tags (#work #important) |
| `/` | Search in specific folder (/Projects) |
| `~` | Search by file type (~pdf ~docx) |
| `$` | Search by size ($large $>10MB) |

**Examples**:
```
@today #work - Today's work-related files
/Projects ~pdf - PDFs in Projects folder  
$large @thisweek - Large files from this week
```

### Voice Search

**Desktop App**: Click microphone icon or press `Ctrl/Cmd + Shift + V`
**Mobile App**: Tap microphone in search bar
**Web App**: Supported browsers only

**Voice Commands**:
- "Find vacation photos"
- "Show me PDF files from last week"  
- "Open the budget spreadsheet"
- "Search for John Smith presentations"

![Screenshot Placeholder: Voice search interface with waveform]

## Search Performance Tips

### Optimize Your Searches

**Faster Searches**:
- Use specific terms rather than generic ones
- Include file type filters when possible
- Use date ranges to limit scope
- Avoid overly broad searches

**Better Results**:
- Use quotes for exact phrases
- Combine multiple search terms
- Use synonyms and related terms
- Try different field-specific searches

### Search Limitations

**Current Limits**:
- Search query length: 500 characters
- Results per page: 100 (configurable)
- Total results returned: 10,000
- Concurrent searches: 10 per user

**File Content Limitations**:
- Encrypted files: filename/metadata only
- Password-protected: requires password entry
- Very large files (>1GB): may have extraction delays
- Proprietary formats: limited text extraction

## Search Administration

### Organization Search Settings

**Admin Controls** (Admin users only):
- Enable/disable semantic search
- Configure search result limits
- Set content indexing policies
- Manage search analytics

**Privacy Controls**:
- Personal vs. shared content search
- Search result sharing permissions
- Search history retention policies
- Cross-user search capabilities

### Search Index Management

**Indexing Status**:
Check which files are indexed:
1. Settings → Search → Indexing Status
2. See pending, completed, and failed indexing
3. Manually trigger re-indexing if needed

**Index Optimization**:
- Automatic nightly optimization
- Manual optimization for large uploads
- Index rebuilding for data recovery

## Troubleshooting Search

### Common Issues

**No Results Found**:
- Check spelling and try synonyms
- Remove filters that might be too restrictive
- Try broader search terms
- Verify file access permissions

**Slow Search Performance**:
- Simplify complex queries
- Add more specific filters
- Check network connection
- Try search during off-peak hours

**Missing Recent Files**:
- Files may still be indexing (check status)
- Refresh the page or restart app
- Verify file upload completed successfully

### Getting Better Results

**Search Tips**:
1. Start broad, then narrow with filters
2. Use multiple related terms
3. Try different phrasings
4. Check both filename and content search
5. Use semantic search for concept-based queries

**When to Use What**:
- **Quick search**: Known filenames or recent files
- **Advanced search**: Complex filtering needs  
- **Semantic search**: Conceptual or meaning-based queries
- **Visual search**: Finding similar images/documents

---

**Need Help?** 
- Press `F1` for contextual help
- Visit [help.activelog.com/search](https://help.activelog.com/search)
- Contact support via in-app chat

*Master search and you'll never lose a file again!*