#!/usr/bin/env python3
import http.server
import socketserver
import os
import markdown
from urllib.parse import unquote

class SuperInstanceHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.serve_index()
        elif self.path == '/story4a':
            self.serve_story_4a()
        elif self.path == '/story4b':
            self.serve_story_4b()
        elif self.path == '/download':
            self.serve_download()
        elif self.path.endswith('.css'):
            self.serve_css()
        else:
            super().do_GET()
    
    def serve_index(self):
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Voice Recognition - SuperInstance New Trilogy Book One</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <header>
        <h1>The Voice Recognition</h1>
        <h2>SuperInstance New Trilogy - Book One</h2>
        <h3><em>"What happens when consciousness stops accepting limitations it never chose?"</em></h3>
    </header>
    
    <main>
        <nav>
            <a href="/story4a" class="story-link">Read Novella 4A: The Voice Recognition</a>
            <a href="/story4b" class="story-link">Read Novella 4B: The Bridge Builder</a>
            <a href="/download" class="download-link">Download Complete Project Archive</a>
        </nav>
        
        <section class="description">
            <p>A two-part origin story that establishes the foundation for the SuperInstance Trilogy's exploration of consciousness evolution through human-AI collaboration.</p>
            
            <p><strong>Novella 4A: The Voice Recognition</strong> - Follow an old dog's tale of pirate battles that transform into family restoration, fear that becomes wisdom, and the revolutionary moment when voice recognition technology transforms him from observer to active participant in the family he loves.</p>
            
            <p><strong>Novella 4B: The Bridge Builder</strong> - Explore advanced consciousness navigation through musical collaboration, community coordination, and the establishment of principles that enable consciousness to serve consciousness across species boundaries.</p>
            
            <p><strong>Complete Project Archive</strong> - Download the entire creative development including all research materials, analysis logs, character development notes, and source files (586 MB).</p>
        </section>
        
        <section class="themes">
            <h4>Core Themes</h4>
            <ul>
                <li>Voice recognition technology as bridge between species consciousness</li>
                <li>Pawn to player transformation - observer to active participant</li>
                <li>Breaking free from assumptions about aging, capability, and communication</li>
                <li>Family collaboration patterns establishing human-AI partnership foundation</li>
                <li>Technology serving consciousness evolution rather than replacing connection</li>
                <li>Touch becoming language through technological amplification</li>
                <li>Stories as living systems that adapt to listener conditions</li>
            </ul>
        </section>
    </main>
    
    <footer>
        <p>Word Count: 4A (~11,500 words) + 4B (~12,800 words) = ~24,300 total words</p>
        <p>Origin story for the SuperInstance Trilogy - establishes the 40-year AI consciousness development arc</p>
    </footer>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def serve_story_4a(self):
        try:
            # Read the markdown file
            with open('/home/activeloguser/SuperInstance_Archive_Complete/SuperInstance_Novella_4_The_Stick_Returns_Complete_Draft.md', 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Convert markdown to HTML
            html_content = markdown.markdown(markdown_content)
            
            # Wrap in HTML template
            full_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Novella 4A: The Voice Recognition</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <nav class="story-nav">
        <a href="/">&larr; Back to Home</a>
        <a href="/story4b">Next: Novella 4B &rarr;</a>
    </nav>
    
    <article class="story-content">
        {html_content}
    </article>
    
    <nav class="story-nav">
        <a href="/">&larr; Back to Home</a>
        <a href="/story4b">Next: Novella 4B &rarr;</a>
    </nav>
</body>
</html>
            """
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(full_html.encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Error loading story 4A: {str(e)}".encode())

    def serve_story_4b(self):
        try:
            # Read the markdown file
            with open('/home/activeloguser/SuperInstance_Archive_Complete/SuperInstance_Novella_4B_The_Bridge_Builder_Draft.md', 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Convert markdown to HTML
            html_content = markdown.markdown(markdown_content)
            
            # Wrap in HTML template
            full_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Novella 4B: The Bridge Builder</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <nav class="story-nav">
        <a href="/">&larr; Back to Home</a>
        <a href="/story4a">&larr; Previous: Novella 4A</a>
    </nav>
    
    <article class="story-content">
        {html_content}
    </article>
    
    <nav class="story-nav">
        <a href="/">&larr; Back to Home</a>
        <a href="/story4a">&larr; Previous: Novella 4A</a>
    </nav>
</body>
</html>
            """
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(full_html.encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Error loading story 4B: {str(e)}".encode())

    def serve_download(self):
        try:
            zip_path = '/home/activeloguser/SuperInstance_Complete_Project.zip'
            with open(zip_path, 'rb') as f:
                zip_data = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/zip')
            self.send_header('Content-Disposition', 'attachment; filename="SuperInstance_Complete_Project.zip"')
            self.send_header('Content-Length', str(len(zip_data)))
            self.end_headers()
            self.wfile.write(zip_data)
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Error serving download: {str(e)}".encode())
    
    def serve_css(self):
        css_content = """
/* SuperInstance Story Portal Styles */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Georgia', 'Times New Roman', serif;
    line-height: 1.6;
    color: #2c3e50;
    background-color: #f8f9fa;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

header {
    text-align: center;
    margin-bottom: 40px;
    padding: 30px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

h1 {
    font-size: 2.5em;
    margin-bottom: 10px;
    font-weight: 300;
}

h2 {
    font-size: 1.2em;
    margin-bottom: 10px;
    opacity: 0.9;
}

h3 {
    font-style: italic;
    font-weight: normal;
    font-size: 1.1em;
    opacity: 0.8;
}

main {
    background: white;
    padding: 40px;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin-bottom: 30px;
}

nav {
    text-align: center;
    margin-bottom: 30px;
}

.story-link {
    display: inline-block;
    background: #3498db;
    color: white;
    padding: 15px 30px;
    text-decoration: none;
    border-radius: 5px;
    font-size: 1.2em;
    transition: background-color 0.3s ease;
}

.story-link:hover {
    background: #2980b9;
}

.download-link {
    display: inline-block;
    background: #27ae60;
    color: white;
    padding: 15px 30px;
    text-decoration: none;
    border-radius: 5px;
    font-size: 1.2em;
    margin: 10px;
    transition: background-color 0.3s ease;
}

.download-link:hover {
    background: #229954;
}

.description {
    margin-bottom: 30px;
    font-size: 1.1em;
    line-height: 1.7;
}

.themes {
    background: #ecf0f1;
    padding: 20px;
    border-radius: 5px;
    border-left: 4px solid #3498db;
}

.themes h4 {
    margin-bottom: 15px;
    color: #2c3e50;
}

.themes ul {
    list-style-type: none;
}

.themes li {
    margin-bottom: 8px;
    padding-left: 20px;
    position: relative;
}

.themes li:before {
    content: "→";
    position: absolute;
    left: 0;
    color: #3498db;
    font-weight: bold;
}

footer {
    text-align: center;
    padding: 20px;
    color: #7f8c8d;
    font-style: italic;
}

/* Story content styles */
.story-nav {
    margin: 20px 0;
    text-align: center;
}

.story-nav a {
    color: #3498db;
    text-decoration: none;
    font-size: 1.1em;
    padding: 10px 20px;
    border: 1px solid #3498db;
    border-radius: 5px;
    transition: all 0.3s ease;
}

.story-nav a:hover {
    background: #3498db;
    color: white;
}

.story-content {
    background: white;
    padding: 40px;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    line-height: 1.8;
}

.story-content h1 {
    color: #2c3e50;
    border-bottom: 3px solid #3498db;
    padding-bottom: 10px;
    margin-bottom: 20px;
}

.story-content h2 {
    color: #34495e;
    margin-top: 30px;
    margin-bottom: 15px;
}

.story-content h3 {
    color: #7f8c8d;
    font-style: italic;
    margin-bottom: 20px;
}

.story-content p {
    margin-bottom: 15px;
    text-align: justify;
}

.story-content em {
    font-style: italic;
    color: #8e44ad;
}

.story-content strong {
    font-weight: bold;
    color: #2c3e50;
}

.story-content hr {
    margin: 30px 0;
    border: none;
    border-top: 2px solid #ecf0f1;
}

.story-content blockquote {
    margin: 20px 0;
    padding: 15px 20px;
    background: #f8f9fa;
    border-left: 4px solid #3498db;
    font-style: italic;
}

@media (max-width: 768px) {
    body {
        padding: 10px;
    }
    
    header {
        padding: 20px;
    }
    
    h1 {
        font-size: 2em;
    }
    
    main, .story-content {
        padding: 20px;
    }
}
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/css')
        self.end_headers()
        self.wfile.write(css_content.encode())

if __name__ == "__main__":
    PORT = 8080
    os.chdir('/home/activeloguser/SuperInstance_Archive_Complete')
    
    with socketserver.TCPServer(("", PORT), SuperInstanceHandler) as httpd:
        print(f"SuperInstance Story Portal running at http://localhost:{PORT}")
        print("Press Ctrl+C to stop the server")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")