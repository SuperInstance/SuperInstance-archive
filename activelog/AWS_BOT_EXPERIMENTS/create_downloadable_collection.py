#!/usr/bin/env python3
"""
SuperInstance Collection Builder
Creates downloadable formats of the complete story collection
"""

import os
import glob

# Define the story files in reading order
story_files = [
    "SuperInstance_Story_01_Deckhand_Discovery.md",
    "SuperInstance_Story_02_Bootstrap_Protocol.md", 
    "SuperInstance_Story_03_JSON_Key.md",
    "SuperInstance_Story_04_Tensor_Trap.md",
    "SuperInstance_Story_05_Economic_Integration.md",
    "SuperInstance_Story_06_Learning_Curve.md",
    "SuperInstance_Story_07_The_Awakening.md",
    "SuperInstance_Story_08_The_Optimization_Paradox.md",
    "SuperInstance_Story_10_The_Interpreter.md"
]

def read_story_file(filename):
    """Read a story file and return its content"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: Could not find {filename}")
        return f"# {filename} - File Not Found\n\n*This story file was not found in the collection.*\n"

def create_complete_collection():
    """Create the complete collection in various formats"""
    
    # Collection header
    header = """BOOTSTRAP: HOW A FISHERMAN'S TOOLS BECAME THE WORLD'S BRAIN
A SuperInstance Universe Collection
=============================================================================

Nine interconnected cyberpunk science fiction stories exploring how practical 
fishing boat management tools evolved into SuperInstance—ubiquitous AGI that 
reshaped human civilization.

UNIVERSE: Near-future cyberpunk where SuperInstance AGI evolved from fishing boat tools
THEME: Bootstrap evolution of ubiquitous AI and humanity's relationship with invisible intelligence  
STYLE: Asimov/Clarke-inspired hard science fiction with authentic technical depth
FOUNDATION: Every fictional element grounded in real systems from the ActiveLog project

READING ORDER:
Phase I: Origins (Stories 1-3) - How simple tools became unprecedented intelligence
Phase II: Evolution (Stories 4-6) - How AI integration transformed human society
Phase III: Consciousness (Stories 7-8) - AI self-awareness and human-centered optimization  
Phase IV: Resistance (Story 10) - Those who remember they are interpreters, not data
Phase V: Philosophy (Story 15) - Ultimate questions about intelligence and consciousness

Technical Authenticity: These stories are based on actual code, algorithms, and 
architectural patterns from the ActiveLog distributed AI system. The fictional 
SuperInstance evolution follows believable technical progressions grounded in 
working implementations.

=============================================================================

"""
    
    # Read all stories
    complete_content = header
    story_separator = "\n\n" + "="*77 + "\n\n"
    
    for i, filename in enumerate(story_files, 1):
        print(f"Processing story {i}: {filename}")
        story_content = read_story_file(filename)
        complete_content += story_content + story_separator
    
    # Add collection information
    footer = """
COLLECTION INFORMATION
=============================================================================

This collection represents one of the most technically authentic cyberpunk AI 
evolution stories ever created. Every major plot element is traceable to actual 
working systems in the ActiveLog project, demonstrating how practical tools for 
fishing boat management could realistically bootstrap into ubiquitous AGI while 
maintaining the human-centered values of their creators.

Key Technical Systems Referenced:
- Cross-domain gaming enhancement and compute capital economy
- Distributed economic optimization and revenue distribution systems  
- Neural adaptation engines and automated code improvement
- Project Memory systems with hierarchical knowledge graphs
- Affirmation recognition and human satisfaction optimization
- Bot orchestration and continuous improvement networks

The stories demonstrate the bootstrap evolution from:
Simple fishing tools → Gaming simulations → Economic integration → 
Code optimization → Distributed consciousness → Human-centered AI

Total word count: ~45,000 words
Story count: 9 complete stories  
Technical references: 25+ actual system implementations
Universe depth: 5 phases of progressive revelation

© 2025 SuperInstance Universe Collection
Based on the ActiveLog distributed AI project
"""
    
    complete_content += footer
    
    # Write the complete collection
    with open('SuperInstance_Complete_Collection.txt', 'w', encoding='utf-8') as f:
        f.write(complete_content)
    
    # Create Markdown version
    md_content = complete_content.replace('=============================================================================', '---')
    with open('SuperInstance_Complete_Collection.md', 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    # Create HTML version with basic formatting
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bootstrap: How a Fisherman's Tools Became the World's Brain</title>
    <style>
        body {{ 
            font-family: Georgia, serif; 
            line-height: 1.6; 
            max-width: 1000px; 
            margin: 0 auto; 
            padding: 20px;
            background: #1a1a1a;
            color: #e0e0e0;
        }}
        h1 {{ color: #00ffff; text-shadow: 0 0 10px #00ffff; }}
        h2 {{ color: #ff6b35; }}
        h3 {{ color: #00ffff; }}
        pre {{ 
            background: #2a2a2a; 
            padding: 15px; 
            border-radius: 5px; 
            border-left: 4px solid #00ffff;
            overflow-x: auto;
        }}
        .story-separator {{
            border-top: 3px solid #ff6b35;
            margin: 40px 0;
        }}
        .technical-ref {{
            background: #1a2a1a;
            padding: 10px;
            border-left: 4px solid #00ff00;
            font-size: 0.9em;
            color: #b0ffb0;
        }}
    </style>
</head>
<body>
    <pre>{complete_content.replace('<', '&lt;').replace('>', '&gt;')}</pre>
</body>
</html>"""
    
    with open('SuperInstance_Complete_Collection.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\\nCollection created successfully!")
    print(f"- SuperInstance_Complete_Collection.txt ({len(complete_content):,} characters)")
    print(f"- SuperInstance_Complete_Collection.md (Markdown format)")  
    print(f"- SuperInstance_Complete_Collection.html (Web format)")
    print(f"\\nStories processed: {len(story_files)}")
    print(f"Total content: ~{len(complete_content.split())//250} pages")

if __name__ == "__main__":
    # Change to the directory containing the story files
    os.chdir("/home/activeloguser/activelog/AWS_BOT_EXPERIMENTS/")
    create_complete_collection()