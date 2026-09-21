// Content script for Quick Analysis Portal browser extension

let analysisOverlay = null;
let quickSearchBox = null;

// Listen for messages from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.action) {
    case "showAnalysis":
      showAnalysisOverlay(message);
      break;
    case "showError":
      showErrorOverlay(message);
      break;
    case "showQuickSearch":
      showQuickSearchBox();
      break;
    case "enhanceFinancialSite":
      enhanceFinancialSite();
      break;
  }
});

function showAnalysisOverlay(message) {
  removeExistingOverlay();
  
  analysisOverlay = createOverlayElement();
  
  if (message.loading) {
    analysisOverlay.innerHTML = createLoadingHTML(message.symbol);
  } else {
    analysisOverlay.innerHTML = createAnalysisHTML(message.symbol, message.data);
  }
  
  document.body.appendChild(analysisOverlay);
  
  // Add event listeners
  const closeBtn = analysisOverlay.querySelector('.qa-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', removeExistingOverlay);
  }
  
  const openFullBtn = analysisOverlay.querySelector('.qa-open-full');
  if (openFullBtn) {
    openFullBtn.addEventListener('click', () => {
      window.open(`https://analysis.activeledger.ai?symbol=${message.symbol}`, '_blank');
      removeExistingOverlay();
    });
  }
  
  // Auto-hide after 30 seconds
  setTimeout(removeExistingOverlay, 30000);
}

function showErrorOverlay(message) {
  removeExistingOverlay();
  
  analysisOverlay = createOverlayElement();
  analysisOverlay.innerHTML = createErrorHTML(message.symbol, message.error);
  
  document.body.appendChild(analysisOverlay);
  
  const closeBtn = analysisOverlay.querySelector('.qa-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', removeExistingOverlay);
  }
  
  // Auto-hide after 10 seconds
  setTimeout(removeExistingOverlay, 10000);
}

function createOverlayElement() {
  const overlay = document.createElement('div');
  overlay.className = 'quick-analysis-overlay';
  overlay.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    width: 400px;
    max-height: 80vh;
    background: white;
    border-radius: 12px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    z-index: 10000;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    overflow: hidden;
    border: 1px solid #e5e7eb;
    animation: slideIn 0.3s ease-out;
  `;
  
  // Add animation keyframes if not already added
  if (!document.querySelector('#qa-animations')) {
    const style = document.createElement('style');
    style.id = 'qa-animations';
    style.textContent = `
      @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      .quick-analysis-overlay {
        animation: slideIn 0.3s ease-out;
      }
    `;
    document.head.appendChild(style);
  }
  
  return overlay;
}

function createLoadingHTML(symbol) {
  return `
    <div style="padding: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="margin: 0; color: #1e40af;">📊 Analyzing ${symbol}</h3>
        <button class="qa-close" style="background: none; border: none; font-size: 20px; cursor: pointer; color: #666;">×</button>
      </div>
      <div style="text-align: center; padding: 40px 20px;">
        <div style="border: 3px solid #f3f4f6; border-top: 3px solid #1e40af; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 20px;"></div>
        <p style="color: #666; margin: 0;">Fetching real-time data...</p>
      </div>
    </div>
    <style>
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    </style>
  `;
}

function createAnalysisHTML(symbol, data) {
  const quote = data.quote;
  const changeClass = quote.change >= 0 ? 'positive' : 'negative';
  const changeSymbol = quote.change >= 0 ? '+' : '';
  const changeColor = quote.change >= 0 ? '#10b981' : '#ef4444';
  
  return `
    <div style="padding: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="margin: 0; color: #1e40af;">📊 ${symbol}</h3>
        <button class="qa-close" style="background: none; border: none; font-size: 20px; cursor: pointer; color: #666;">×</button>
      </div>
      
      <div style="margin-bottom: 20px;">
        <div style="font-size: 24px; font-weight: bold; color: #1e40af; margin-bottom: 5px;">
          $${quote.current_price}
        </div>
        <div style="color: ${changeColor}; font-weight: 600;">
          ${changeSymbol}${quote.change} (${changeSymbol}${quote.change_percent.toFixed(2)}%)
        </div>
        <div style="color: #666; font-size: 14px; margin-top: 5px;">
          ${quote.company_name}
        </div>
      </div>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; font-size: 14px;">
        <div>
          <div style="color: #666;">Volume</div>
          <div style="font-weight: 600;">${quote.volume ? quote.volume.toLocaleString() : 'N/A'}</div>
        </div>
        <div>
          <div style="color: #666;">P/E Ratio</div>
          <div style="font-weight: 600;">${quote.pe_ratio || 'N/A'}</div>
        </div>
        <div>
          <div style="color: #666;">Market Cap</div>
          <div style="font-weight: 600;">${quote.market_cap ? '$' + (quote.market_cap/1e9).toFixed(1) + 'B' : 'N/A'}</div>
        </div>
        <div>
          <div style="color: #666;">52W Range</div>
          <div style="font-weight: 600;">$${quote['52_week_low']} - $${quote['52_week_high']}</div>
        </div>
      </div>
      
      ${data.news && data.news.news && data.news.news.length > 0 ? `
        <div style="margin-bottom: 20px;">
          <h4 style="margin: 0 0 10px 0; color: #333; font-size: 14px;">📰 Latest News</h4>
          <div style="font-size: 13px; color: #666; border-left: 3px solid #1e40af; padding-left: 10px;">
            ${data.news.news[0].title}
          </div>
        </div>
      ` : ''}
      
      <div style="display: flex; gap: 10px;">
        <button class="qa-open-full" style="flex: 1; background: #1e40af; color: white; border: none; border-radius: 6px; padding: 10px; cursor: pointer; font-size: 14px;">
          Full Analysis →
        </button>
        <button class="qa-close" style="background: #f3f4f6; color: #666; border: none; border-radius: 6px; padding: 10px 20px; cursor: pointer; font-size: 14px;">
          Close
        </button>
      </div>
      
      <div style="text-align: center; margin-top: 15px; font-size: 12px; color: #666;">
        Powered by Quick Analysis Portal
      </div>
    </div>
  `;
}

function createErrorHTML(symbol, error) {
  return `
    <div style="padding: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h3 style="margin: 0; color: #ef4444;">❌ Error</h3>
        <button class="qa-close" style="background: none; border: none; font-size: 20px; cursor: pointer; color: #666;">×</button>
      </div>
      
      <div style="margin-bottom: 20px;">
        <p style="color: #666; margin: 0;">Failed to analyze <strong>${symbol}</strong></p>
        <p style="color: #ef4444; font-size: 14px; margin: 10px 0 0 0;">${error}</p>
      </div>
      
      <button class="qa-close" style="width: 100%; background: #f3f4f6; color: #666; border: none; border-radius: 6px; padding: 10px; cursor: pointer;">
        Close
      </button>
    </div>
  `;
}

function removeExistingOverlay() {
  if (analysisOverlay) {
    analysisOverlay.remove();
    analysisOverlay = null;
  }
  if (quickSearchBox) {
    quickSearchBox.remove();
    quickSearchBox = null;
  }
}

function showQuickSearchBox() {
  removeExistingOverlay();
  
  quickSearchBox = document.createElement('div');
  quickSearchBox.className = 'quick-analysis-search';
  quickSearchBox.style.cssText = `
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 400px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    z-index: 10001;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    padding: 20px;
    border: 1px solid #e5e7eb;
  `;
  
  quickSearchBox.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
      <h3 style="margin: 0; color: #1e40af;">🔍 Quick Stock Search</h3>
      <button class="qa-close" style="background: none; border: none; font-size: 20px; cursor: pointer; color: #666;">×</button>
    </div>
    
    <div style="margin-bottom: 20px;">
      <input type="text" 
             class="qa-search-input" 
             placeholder="Enter stock symbol (e.g., AAPL, TSLA)" 
             style="width: 100%; padding: 12px; border: 2px solid #e5e7eb; border-radius: 8px; font-size: 16px; outline: none;">
    </div>
    
    <div style="display: flex; gap: 10px;">
      <button class="qa-search-btn" style="flex: 1; background: #1e40af; color: white; border: none; border-radius: 6px; padding: 12px; cursor: pointer; font-size: 14px;">
        Analyze
      </button>
      <button class="qa-close" style="background: #f3f4f6; color: #666; border: none; border-radius: 6px; padding: 12px 20px; cursor: pointer; font-size: 14px;">
        Cancel
      </button>
    </div>
    
    <div style="text-align: center; margin-top: 15px; font-size: 12px; color: #666;">
      Press Enter to search • Esc to cancel
    </div>
  `;
  
  document.body.appendChild(quickSearchBox);
  
  const input = quickSearchBox.querySelector('.qa-search-input');
  const searchBtn = quickSearchBox.querySelector('.qa-search-btn');
  const closeBtn = quickSearchBox.querySelector('.qa-close');
  
  // Focus input
  input.focus();
  
  // Event listeners
  closeBtn.addEventListener('click', removeExistingOverlay);
  
  searchBtn.addEventListener('click', () => {
    const symbol = input.value.trim().toUpperCase();
    if (symbol) {
      removeExistingOverlay();
      chrome.runtime.sendMessage({
        action: 'analyzeSymbol',
        symbol: symbol
      });
    }
  });
  
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const symbol = input.value.trim().toUpperCase();
      if (symbol) {
        removeExistingOverlay();
        // Trigger analysis
        window.postMessage({
          type: 'QUICK_ANALYSIS',
          symbol: symbol
        }, '*');
      }
    } else if (e.key === 'Escape') {
      removeExistingOverlay();
    }
  });
}

function enhanceFinancialSite() {
  // Add quick access buttons to financial sites
  const stockSymbols = document.querySelectorAll('[data-symbol], .ticker, .symbol');
  
  stockSymbols.forEach(element => {
    if (!element.querySelector('.qa-quick-btn')) {
      const symbol = element.getAttribute('data-symbol') || 
                    element.textContent.trim().match(/[A-Z]{1,5}/)?.[0];
      
      if (symbol && symbol.length <= 5) {
        const btn = document.createElement('button');
        btn.className = 'qa-quick-btn';
        btn.innerHTML = '📊';
        btn.title = `Quick analysis for ${symbol}`;
        btn.style.cssText = `
          margin-left: 5px;
          background: #1e40af;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 2px 6px;
          cursor: pointer;
          font-size: 12px;
        `;
        
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          showAnalysisOverlay({ symbol: symbol, loading: true });
          
          // Fetch analysis
          fetch('https://analysis.activeledger.ai/api/quick-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: symbol })
          })
          .then(response => response.json())
          .then(data => {
            if (data.error) {
              showErrorOverlay({ symbol: symbol, error: data.error });
            } else {
              showAnalysisOverlay({ symbol: symbol, data: data, loading: false });
            }
          })
          .catch(error => {
            showErrorOverlay({ symbol: symbol, error: 'Failed to fetch data' });
          });
        });
        
        element.appendChild(btn);
      }
    }
  });
}

// Handle clicks outside overlay
document.addEventListener('click', (e) => {
  if (analysisOverlay && !analysisOverlay.contains(e.target)) {
    removeExistingOverlay();
  }
});

// Handle escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    removeExistingOverlay();
  }
});

// Auto-detect stock symbols on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', detectStockSymbols);
} else {
  detectStockSymbols();
}

function detectStockSymbols() {
  // Look for patterns that might be stock symbols
  const textNodes = getTextNodes(document.body);
  const stockPattern = /\b[A-Z]{1,5}\b/g;
  
  textNodes.forEach(node => {
    const matches = node.textContent.match(stockPattern);
    if (matches) {
      // Add subtle highlighting to potential stock symbols
      matches.forEach(match => {
        if (match.length >= 2 && match.length <= 5) {
          node.textContent = node.textContent.replace(match, match);
          // Could add more sophisticated highlighting here
        }
      });
    }
  });
}

function getTextNodes(element) {
  const textNodes = [];
  const walker = document.createTreeWalker(
    element,
    NodeFilter.SHOW_TEXT,
    null,
    false
  );
  
  let node;
  while (node = walker.nextNode()) {
    textNodes.push(node);
  }
  
  return textNodes;
}