// Background script for Quick Analysis Portal browser extension

// Install context menu
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "analyzeStock",
    title: "Analyze '%s' with Quick Analysis Portal",
    contexts: ["selection"]
  });
  
  chrome.contextMenus.create({
    id: "openPortal",
    title: "Open Quick Analysis Portal",
    contexts: ["page"]
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "analyzeStock") {
    const selectedText = info.selectionText.trim().toUpperCase();
    
    // Check if selected text looks like a stock symbol
    if (isValidStockSymbol(selectedText)) {
      analyzeStock(selectedText, tab.id);
    } else {
      showNotification("Invalid stock symbol", `"${selectedText}" doesn't appear to be a valid stock symbol.`);
    }
  } else if (info.menuItemId === "openPortal") {
    chrome.tabs.create({
      url: "https://analysis.activeledger.ai"
    });
  }
});

// Handle extension icon click
chrome.action.onClicked.addListener((tab) => {
  // Show popup or open portal directly
  chrome.tabs.create({
    url: "https://analysis.activeledger.ai"
  });
});

function isValidStockSymbol(text) {
  // Basic validation for stock symbols
  const stockPattern = /^[A-Z]{1,5}(\.[A-Z]{1,2})?$/;
  return stockPattern.test(text) && text.length <= 6;
}

async function analyzeStock(symbol, tabId) {
  try {
    // Show loading indicator
    chrome.tabs.sendMessage(tabId, {
      action: "showAnalysis",
      symbol: symbol,
      loading: true
    });
    
    // Fetch analysis data
    const response = await fetch('https://analysis.activeledger.ai/api/quick-analysis', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ symbol: symbol })
    });
    
    const data = await response.json();
    
    if (data.error) {
      chrome.tabs.sendMessage(tabId, {
        action: "showError",
        error: data.error,
        symbol: symbol
      });
    } else {
      chrome.tabs.sendMessage(tabId, {
        action: "showAnalysis",
        symbol: symbol,
        data: data,
        loading: false
      });
    }
  } catch (error) {
    chrome.tabs.sendMessage(tabId, {
      action: "showError",
      error: "Failed to fetch analysis data",
      symbol: symbol
    });
  }
}

function showNotification(title, message) {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon48.png',
    title: title,
    message: message
  });
}

// Handle keyboard shortcuts
chrome.commands.onCommand.addListener((command) => {
  if (command === "open-portal") {
    chrome.tabs.create({
      url: "https://analysis.activeledger.ai"
    });
  } else if (command === "quick-search") {
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
      chrome.tabs.sendMessage(tabs[0].id, {
        action: "showQuickSearch"
      });
    });
  }
});

// Auto-detect stock symbols on page
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url && 
      (tab.url.includes('finance.yahoo.com') || 
       tab.url.includes('marketwatch.com') ||
       tab.url.includes('bloomberg.com'))) {
    
    // Inject enhanced functionality for financial sites
    chrome.tabs.sendMessage(tabId, {
      action: "enhanceFinancialSite"
    });
  }
});

// Store user preferences
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'sync' && changes.preferences) {
    console.log('User preferences updated:', changes.preferences.newValue);
  }
});