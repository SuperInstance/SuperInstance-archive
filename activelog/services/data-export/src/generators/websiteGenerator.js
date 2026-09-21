const fs = require('fs-extra');
const path = require('path');
const handlebars = require('handlebars');
const puppeteer = require('puppeteer');
const moment = require('moment');
const sharp = require('sharp');
const logger = require('../utils/logger');

class WebsiteGenerator {
  constructor(options = {}) {
    this.options = {
      theme: options.theme || 'default',
      includeSearch: options.includeSearch !== false,
      generateSitemap: options.generateSitemap !== false,
      optimizeImages: options.optimizeImages !== false,
      generateThumbnails: options.generateThumbnails !== false,
      responsiveDesign: options.responsiveDesign !== false,
      includeAnalytics: options.includeAnalytics || false,
      customCSS: options.customCSS || null,
      customJS: options.customJS || null,
      ...options
    };

    this.templateDir = path.join(__dirname, '../../templates/website');
  }

  async generateStaticWebsite(data, outputDir, metadata = {}) {
    try {
      await fs.ensureDir(outputDir);
      
      const siteData = this.prepareSiteData(data, metadata);
      
      await this.copyStaticAssets(outputDir);
      await this.generatePages(siteData, outputDir);
      
      if (this.options.generateSitemap) {
        await this.generateSitemap(siteData, outputDir);
      }
      
      if (this.options.includeSearch) {
        await this.generateSearchIndex(siteData, outputDir);
      }

      const result = {
        success: true,
        outputDir,
        pages: siteData.pages.length,
        assets: await this.countAssets(outputDir)
      };

      logger.info(`Static website generated: ${outputDir}`);
      return result;
    } catch (error) {
      logger.error('Website generation failed:', error);
      throw error;
    }
  }

  prepareSiteData(data, metadata) {
    const siteData = {
      title: metadata.title || 'Data Export Website',
      description: metadata.description || 'Generated from exported data',
      author: metadata.author || 'ActiveLog Export Service',
      generatedAt: moment().format('YYYY-MM-DD HH:mm:ss'),
      theme: this.options.theme,
      pages: [],
      navigation: [],
      assets: {
        images: [],
        documents: [],
        other: []
      }
    };

    if (Array.isArray(data)) {
      data.forEach((item, index) => {
        this.processDataItem(item, siteData, index);
      });
    } else if (typeof data === 'object') {
      Object.entries(data).forEach(([key, value], index) => {
        this.processDataObject(key, value, siteData, index);
      });
    }

    this.generateNavigation(siteData);
    return siteData;
  }

  processDataItem(item, siteData, index) {
    if (item.type === 'page') {
      this.addPage(item, siteData);
    } else if (item.type === 'gallery') {
      this.addGalleryPage(item, siteData);
    } else if (item.type === 'blog_post') {
      this.addBlogPost(item, siteData);
    } else if (item.type === 'document') {
      this.addDocument(item, siteData);
    } else {
      this.addGenericPage(item, siteData, `page-${index}`);
    }
  }

  processDataObject(key, value, siteData, index) {
    const page = {
      id: key.toLowerCase().replace(/\s+/g, '-'),
      title: this.formatTitle(key),
      content: this.formatContent(value),
      template: this.selectTemplate(value),
      metadata: {
        createdAt: moment().toISOString(),
        type: 'data_object'
      }
    };

    siteData.pages.push(page);
  }

  addPage(item, siteData) {
    const page = {
      id: item.id || this.generatePageId(item.title),
      title: item.title,
      content: item.content,
      template: item.template || 'page',
      metadata: item.metadata || {}
    };

    siteData.pages.push(page);
  }

  addGalleryPage(item, siteData) {
    const page = {
      id: item.id || 'gallery',
      title: item.title || 'Gallery',
      template: 'gallery',
      content: {
        description: item.description,
        images: item.images.map(img => this.processGalleryImage(img))
      },
      metadata: item.metadata || {}
    };

    siteData.pages.push(page);
    siteData.assets.images.push(...item.images);
  }

  addBlogPost(item, siteData) {
    const page = {
      id: item.id || this.generatePageId(item.title),
      title: item.title,
      template: 'blog_post',
      content: {
        body: item.content,
        excerpt: item.excerpt || this.generateExcerpt(item.content),
        author: item.author,
        publishDate: item.publishDate || moment().format('YYYY-MM-DD'),
        tags: item.tags || []
      },
      metadata: item.metadata || {}
    };

    siteData.pages.push(page);
  }

  addDocument(item, siteData) {
    const page = {
      id: this.generatePageId(item.title),
      title: item.title,
      template: 'document',
      content: {
        description: item.description,
        downloadUrl: item.path,
        fileSize: item.size,
        fileType: item.type
      },
      metadata: item.metadata || {}
    };

    siteData.pages.push(page);
    siteData.assets.documents.push(item);
  }

  addGenericPage(item, siteData, fallbackId) {
    const page = {
      id: fallbackId,
      title: item.title || this.formatTitle(fallbackId),
      content: this.formatContent(item),
      template: 'generic',
      metadata: {
        originalType: typeof item,
        createdAt: moment().toISOString()
      }
    };

    siteData.pages.push(page);
  }

  generateNavigation(siteData) {
    siteData.navigation = siteData.pages.map(page => ({
      id: page.id,
      title: page.title,
      url: `${page.id}.html`,
      template: page.template
    }));

    // Group by template type for better organization
    const navGroups = {};
    siteData.navigation.forEach(item => {
      const group = item.template;
      if (!navGroups[group]) {
        navGroups[group] = [];
      }
      navGroups[group].push(item);
    });

    siteData.navigationGroups = navGroups;
  }

  async copyStaticAssets(outputDir) {
    const assetsDir = path.join(outputDir, 'assets');
    await fs.ensureDir(assetsDir);

    const templateAssetsDir = path.join(this.templateDir, this.options.theme, 'assets');
    
    if (await fs.pathExists(templateAssetsDir)) {
      await fs.copy(templateAssetsDir, assetsDir);
    }

    if (this.options.customCSS) {
      await fs.copy(this.options.customCSS, path.join(assetsDir, 'css', 'custom.css'));
    }

    if (this.options.customJS) {
      await fs.copy(this.options.customJS, path.join(assetsDir, 'js', 'custom.js'));
    }
  }

  async generatePages(siteData, outputDir) {
    const layoutTemplate = await this.loadTemplate('layout');
    const templates = {};

    for (const page of siteData.pages) {
      if (!templates[page.template]) {
        templates[page.template] = await this.loadTemplate(page.template);
      }

      const pageContent = templates[page.template](page);
      const fullPage = layoutTemplate({
        ...siteData,
        page,
        content: pageContent,
        includeAnalytics: this.options.includeAnalytics
      });

      const outputPath = path.join(outputDir, `${page.id}.html`);
      await fs.writeFile(outputPath, fullPage);
    }

    // Generate index page
    const indexTemplate = await this.loadTemplate('index');
    const indexContent = indexTemplate(siteData);
    const indexPage = layoutTemplate({
      ...siteData,
      page: { title: siteData.title, id: 'index' },
      content: indexContent
    });

    await fs.writeFile(path.join(outputDir, 'index.html'), indexPage);
  }

  async loadTemplate(templateName) {
    const templatePath = path.join(this.templateDir, this.options.theme, `${templateName}.hbs`);
    
    if (await fs.pathExists(templatePath)) {
      const templateSource = await fs.readFile(templatePath, 'utf8');
      return handlebars.compile(templateSource);
    } else {
      return this.getDefaultTemplate(templateName);
    }
  }

  getDefaultTemplate(templateName) {
    const defaultTemplates = {
      layout: `
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>{{page.title}} - {{title}}</title>
          <link rel="stylesheet" href="assets/css/style.css">
          {{#if responsiveDesign}}
          <link rel="stylesheet" href="assets/css/responsive.css">
          {{/if}}
        </head>
        <body>
          <header>
            <h1>{{title}}</h1>
            <nav>
              {{#each navigation}}
              <a href="{{url}}">{{title}}</a>
              {{/each}}
            </nav>
          </header>
          <main>
            {{{content}}}
          </main>
          <footer>
            <p>Generated on {{generatedAt}} by ActiveLog Export Service</p>
          </footer>
          {{#if includeSearch}}
          <script src="assets/js/search.js"></script>
          {{/if}}
          {{#if includeAnalytics}}
          <!-- Analytics code would go here -->
          {{/if}}
        </body>
        </html>
      `,
      
      index: `
        <h2>Welcome</h2>
        <p>{{description}}</p>
        <div class="page-list">
          {{#each navigationGroups}}
          <div class="page-group">
            <h3>{{@key}}</h3>
            <ul>
              {{#each this}}
              <li><a href="{{url}}">{{title}}</a></li>
              {{/each}}
            </ul>
          </div>
          {{/each}}
        </div>
      `,
      
      page: `
        <article>
          <h1>{{title}}</h1>
          <div class="content">
            {{{content}}}
          </div>
        </article>
      `,
      
      gallery: `
        <article>
          <h1>{{title}}</h1>
          {{#if content.description}}
          <p>{{content.description}}</p>
          {{/if}}
          <div class="gallery">
            {{#each content.images}}
            <div class="gallery-item">
              <img src="{{src}}" alt="{{alt}}" loading="lazy">
              {{#if caption}}
              <p class="caption">{{caption}}</p>
              {{/if}}
            </div>
            {{/each}}
          </div>
        </article>
      `,
      
      blog_post: `
        <article>
          <header>
            <h1>{{title}}</h1>
            <div class="meta">
              {{#if content.author}}<span class="author">By {{content.author}}</span>{{/if}}
              {{#if content.publishDate}}<span class="date">{{content.publishDate}}</span>{{/if}}
            </div>
          </header>
          <div class="content">
            {{{content.body}}}
          </div>
          {{#if content.tags}}
          <div class="tags">
            {{#each content.tags}}
            <span class="tag">{{this}}</span>
            {{/each}}
          </div>
          {{/if}}
        </article>
      `,
      
      document: `
        <article>
          <h1>{{title}}</h1>
          {{#if content.description}}
          <p>{{content.description}}</p>
          {{/if}}
          <div class="document-info">
            <p><strong>File Type:</strong> {{content.fileType}}</p>
            {{#if content.fileSize}}
            <p><strong>Size:</strong> {{content.fileSize}}</p>
            {{/if}}
            <a href="{{content.downloadUrl}}" class="download-btn" download>Download Document</a>
          </div>
        </article>
      `,
      
      generic: `
        <article>
          <h1>{{title}}</h1>
          <div class="content">
            <pre>{{content}}</pre>
          </div>
        </article>
      `
    };

    const template = defaultTemplates[templateName] || defaultTemplates.generic;
    return handlebars.compile(template);
  }

  async generateSitemap(siteData, outputDir) {
    const baseUrl = this.options.baseUrl || 'https://example.com';
    
    const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>${baseUrl}/index.html</loc>
    <lastmod>${moment().format('YYYY-MM-DD')}</lastmod>
    <priority>1.0</priority>
  </url>
  ${siteData.pages.map(page => `
  <url>
    <loc>${baseUrl}/${page.id}.html</loc>
    <lastmod>${moment().format('YYYY-MM-DD')}</lastmod>
    <priority>0.8</priority>
  </url>`).join('')}
</urlset>`;

    await fs.writeFile(path.join(outputDir, 'sitemap.xml'), sitemap);
  }

  async generateSearchIndex(siteData, outputDir) {
    const searchIndex = siteData.pages.map(page => ({
      id: page.id,
      title: page.title,
      content: this.stripHtml(page.content),
      url: `${page.id}.html`
    }));

    const searchScript = `
      const searchIndex = ${JSON.stringify(searchIndex, null, 2)};
      
      function search(query) {
        const results = searchIndex.filter(page => 
          page.title.toLowerCase().includes(query.toLowerCase()) ||
          page.content.toLowerCase().includes(query.toLowerCase())
        );
        return results;
      }
      
      // Simple search functionality
      document.addEventListener('DOMContentLoaded', function() {
        const searchInput = document.createElement('input');
        searchInput.type = 'search';
        searchInput.placeholder = 'Search...';
        searchInput.id = 'search-input';
        
        const searchResults = document.createElement('div');
        searchResults.id = 'search-results';
        
        document.querySelector('header').appendChild(searchInput);
        document.querySelector('header').appendChild(searchResults);
        
        searchInput.addEventListener('input', function() {
          const query = this.value;
          if (query.length > 2) {
            const results = search(query);
            displaySearchResults(results);
          } else {
            searchResults.innerHTML = '';
          }
        });
        
        function displaySearchResults(results) {
          searchResults.innerHTML = results.map(result => 
            \`<div class="search-result">
              <a href="\${result.url}">\${result.title}</a>
            </div>\`
          ).join('');
        }
      });
    `;

    const assetsJsDir = path.join(outputDir, 'assets', 'js');
    await fs.ensureDir(assetsJsDir);
    await fs.writeFile(path.join(assetsJsDir, 'search.js'), searchScript);
  }

  processGalleryImage(image) {
    return {
      src: image.path || image.src,
      alt: image.alt || image.caption || 'Image',
      caption: image.caption,
      thumbnail: image.thumbnail,
      metadata: image.metadata
    };
  }

  formatTitle(text) {
    return text.replace(/[-_]/g, ' ')
               .replace(/\w\S*/g, (txt) => 
                 txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
               );
  }

  formatContent(content) {
    if (typeof content === 'string') {
      return content;
    } else if (typeof content === 'object') {
      return `<pre>${JSON.stringify(content, null, 2)}</pre>`;
    } else {
      return String(content);
    }
  }

  selectTemplate(content) {
    if (Array.isArray(content) && content.every(item => item.type === 'image')) {
      return 'gallery';
    } else if (typeof content === 'object' && content.body) {
      return 'blog_post';
    } else {
      return 'page';
    }
  }

  generatePageId(title) {
    return title.toLowerCase()
                .replace(/[^a-z0-9\s]/g, '')
                .replace(/\s+/g, '-')
                .substring(0, 50);
  }

  generateExcerpt(content, maxLength = 200) {
    const stripped = this.stripHtml(content);
    return stripped.length > maxLength 
      ? stripped.substring(0, maxLength) + '...'
      : stripped;
  }

  stripHtml(html) {
    return html.replace(/<[^>]*>/g, '').trim();
  }

  async countAssets(outputDir) {
    const assetsDir = path.join(outputDir, 'assets');
    let count = 0;
    
    if (await fs.pathExists(assetsDir)) {
      const files = await this.getAllFiles(assetsDir);
      count = files.length;
    }
    
    return count;
  }

  async getAllFiles(dir, files = []) {
    const items = await fs.readdir(dir);
    
    for (const item of items) {
      const fullPath = path.join(dir, item);
      const stats = await fs.stat(fullPath);
      
      if (stats.isDirectory()) {
        await this.getAllFiles(fullPath, files);
      } else {
        files.push(fullPath);
      }
    }
    
    return files;
  }

  async generateResponsiveImages(images, outputDir) {
    const sizes = [320, 640, 1024, 1920];
    const responsiveDir = path.join(outputDir, 'assets', 'images', 'responsive');
    await fs.ensureDir(responsiveDir);

    for (const image of images) {
      const imagePath = image.path || image.src;
      const basename = path.basename(imagePath, path.extname(imagePath));
      const ext = path.extname(imagePath);

      for (const size of sizes) {
        const outputPath = path.join(responsiveDir, `${basename}_${size}w${ext}`);
        
        try {
          await sharp(imagePath)
            .resize(size, null, { withoutEnlargement: true })
            .jpeg({ quality: 85 })
            .toFile(outputPath);
        } catch (error) {
          logger.warn(`Failed to resize image ${imagePath}: ${error.message}`);
        }
      }
    }
  }
}

module.exports = WebsiteGenerator;