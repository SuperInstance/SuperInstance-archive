const { test, expect } = require('@playwright/test');

test.describe('Complete User Journey', () => {
  let page;
  let context;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await context.close();
  });

  test('User Registration and Login Flow', async () => {
    // Navigate to registration page
    await page.goto('/register');
    
    // Fill registration form
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'SecurePassword123!');
    await page.fill('[data-testid="confirmPassword"]', 'SecurePassword123!');
    await page.fill('[data-testid="firstName"]', 'Test');
    await page.fill('[data-testid="lastName"]', 'User');
    
    // Submit registration
    await page.click('[data-testid="register-button"]');
    
    // Verify registration success
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
    await expect(page).toHaveURL('/dashboard');
  });

  test('Personal Log Creation and Management', async () => {
    // Navigate to Personal Log
    await page.goto('/dashboard');
    await page.click('[data-testid="personal-log-nav"]');
    
    // Create new log entry
    await page.click('[data-testid="new-entry-button"]');
    
    // Fill entry form
    await page.fill('[data-testid="entry-title"]', 'Test Entry');
    await page.fill('[data-testid="entry-content"]', 'This is a test log entry for E2E testing.');
    await page.selectOption('[data-testid="entry-category"]', 'personal');
    await page.click('[data-testid="entry-tags"]');
    await page.fill('[data-testid="entry-tags"]', 'test, e2e, automation');
    
    // Save entry
    await page.click('[data-testid="save-entry-button"]');
    
    // Verify entry creation
    await expect(page.locator('[data-testid="entry-list"]')).toContainText('Test Entry');
    
    // Edit entry
    await page.click('[data-testid="edit-entry-button"]');
    await page.fill('[data-testid="entry-content"]', 'Updated test log entry content.');
    await page.click('[data-testid="save-entry-button"]');
    
    // Verify update
    await expect(page.locator('[data-testid="entry-content"]')).toContainText('Updated test log entry content.');
  });

  test('Business Log Integration', async () => {
    // Switch to Business Log
    await page.click('[data-testid="business-log-nav"]');
    
    // Verify business features are available
    await expect(page.locator('[data-testid="projects-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="team-section"]')).toBeVisible();
    
    // Create business project
    await page.click('[data-testid="new-project-button"]');
    await page.fill('[data-testid="project-name"]', 'E2E Test Project');
    await page.fill('[data-testid="project-description"]', 'Project for end-to-end testing');
    await page.selectOption('[data-testid="project-status"]', 'active');
    await page.click('[data-testid="save-project-button"]');
    
    // Verify project creation
    await expect(page.locator('[data-testid="project-list"]')).toContainText('E2E Test Project');
  });

  test('Search Functionality', async () => {
    // Test global search
    await page.fill('[data-testid="global-search"]', 'test entry');
    await page.click('[data-testid="search-button"]');
    
    // Verify search results
    await expect(page.locator('[data-testid="search-results"]')).toBeVisible();
    await expect(page.locator('[data-testid="search-results"]')).toContainText('Test Entry');
    
    // Test advanced search
    await page.click('[data-testid="advanced-search-toggle"]');
    await page.selectOption('[data-testid="search-category"]', 'personal');
    await page.fill('[data-testid="search-date-from"]', '2024-01-01');
    await page.click('[data-testid="advanced-search-button"]');
    
    // Verify filtered results
    await expect(page.locator('[data-testid="search-results-count"]')).toBeVisible();
  });

  test('Data Synchronization', async () => {
    // Test real-time sync
    const page2 = await context.newPage();
    await page2.goto('/dashboard');
    
    // Create entry in first tab
    await page.goto('/personal-log');
    await page.click('[data-testid="new-entry-button"]');
    await page.fill('[data-testid="entry-title"]', 'Sync Test Entry');
    await page.click('[data-testid="save-entry-button"]');
    
    // Verify sync in second tab
    await page2.reload();
    await expect(page2.locator('[data-testid="entry-list"]')).toContainText('Sync Test Entry');
    
    await page2.close();
  });

  test('Export and Import Functionality', async () => {
    // Test data export
    await page.goto('/settings/data');
    await page.click('[data-testid="export-data-button"]');
    await page.selectOption('[data-testid="export-format"]', 'json');
    await page.click('[data-testid="confirm-export-button"]');
    
    // Wait for download
    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="download-export-button"]');
    const download = await downloadPromise;
    
    // Verify download
    expect(download.suggestedFilename()).toMatch(/.*\.json$/);
  });

  test('User Settings and Preferences', async () => {
    // Navigate to settings
    await page.goto('/settings');
    
    // Update profile
    await page.click('[data-testid="profile-tab"]');
    await page.fill('[data-testid="display-name"]', 'Updated Test User');
    await page.selectOption('[data-testid="timezone"]', 'America/New_York');
    await page.click('[data-testid="save-profile-button"]');
    
    // Verify success message
    await expect(page.locator('[data-testid="profile-success-message"]')).toBeVisible();
    
    // Update preferences
    await page.click('[data-testid="preferences-tab"]');
    await page.check('[data-testid="email-notifications"]');
    await page.selectOption('[data-testid="theme"]', 'dark');
    await page.click('[data-testid="save-preferences-button"]');
    
    // Verify theme change
    await expect(page.locator('body')).toHaveClass(/dark-theme/);
  });

  test('Mobile Responsiveness', async () => {
    // Test on mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Verify mobile navigation
    await page.goto('/dashboard');
    await expect(page.locator('[data-testid="mobile-menu-button"]')).toBeVisible();
    
    // Test mobile menu
    await page.click('[data-testid="mobile-menu-button"]');
    await expect(page.locator('[data-testid="mobile-nav-menu"]')).toBeVisible();
    
    // Test mobile forms
    await page.click('[data-testid="personal-log-mobile-nav"]');
    await page.click('[data-testid="new-entry-button"]');
    
    // Verify mobile form layout
    await expect(page.locator('[data-testid="mobile-entry-form"]')).toBeVisible();
  });

  test('Error Handling and Recovery', async () => {
    // Test network error handling
    await context.setOffline(true);
    
    await page.goto('/dashboard');
    await page.click('[data-testid="new-entry-button"]');
    await page.fill('[data-testid="entry-title"]', 'Offline Entry');
    await page.click('[data-testid="save-entry-button"]');
    
    // Verify offline indicator
    await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();
    
    // Reconnect and verify sync
    await context.setOffline(false);
    await page.waitForSelector('[data-testid="online-indicator"]');
    
    // Verify offline entry was synced
    await expect(page.locator('[data-testid="entry-list"]')).toContainText('Offline Entry');
  });
});

test.describe('Performance Tests', () => {
  test('Page Load Performance', async ({ page }) => {
    // Measure page load time
    const startTime = Date.now();
    await page.goto('/dashboard');
    const loadTime = Date.now() - startTime;
    
    // Assert reasonable load time (less than 3 seconds)
    expect(loadTime).toBeLessThan(3000);
    
    // Check for performance markers
    const performanceEntries = await page.evaluate(() => {
      return JSON.stringify(performance.getEntriesByType('navigation'));
    });
    
    const navigation = JSON.parse(performanceEntries)[0];
    expect(navigation.domContentLoadedEventEnd - navigation.fetchStart).toBeLessThan(2000);
  });

  test('Large Dataset Handling', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Create multiple entries to test pagination
    for (let i = 0; i < 50; i++) {
      await page.evaluate((index) => {
        // Mock API call to create entries
        window.createMockEntry(`Test Entry ${index}`);
      }, i);
    }
    
    // Test pagination
    await page.goto('/personal-log');
    await expect(page.locator('[data-testid="pagination"]')).toBeVisible();
    await page.click('[data-testid="next-page-button"]');
    
    // Verify page navigation
    await expect(page.locator('[data-testid="page-indicator"]')).toContainText('2');
  });
});

test.describe('Accessibility Tests', () => {
  test('Keyboard Navigation', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Test tab navigation
    await page.keyboard.press('Tab');
    const focusedElement = await page.evaluate(() => document.activeElement.tagName);
    expect(['A', 'BUTTON', 'INPUT'].includes(focusedElement)).toBeTruthy();
    
    // Test form navigation
    await page.goto('/personal-log/new');
    await page.keyboard.press('Tab'); // Focus title
    await page.keyboard.type('Keyboard Navigation Test');
    await page.keyboard.press('Tab'); // Focus content
    await page.keyboard.type('Testing keyboard navigation.');
    
    // Save with keyboard
    await page.keyboard.press('Tab'); // Navigate to save button
    await page.keyboard.press('Tab'); // Skip to save button
    await page.keyboard.press('Enter'); // Save entry
    
    // Verify entry creation
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
  });

  test('Screen Reader Compatibility', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Check for proper ARIA labels
    const mainContent = page.locator('main');
    await expect(mainContent).toHaveAttribute('role', 'main');
    
    // Check form labels
    await page.goto('/personal-log/new');
    const titleInput = page.locator('[data-testid="entry-title"]');
    await expect(titleInput).toHaveAttribute('aria-label');
    
    // Check heading structure
    const headings = page.locator('h1, h2, h3, h4, h5, h6');
    const headingCount = await headings.count();
    expect(headingCount).toBeGreaterThan(0);
  });
});

// Custom test fixtures and utilities
test.describe.configure({ mode: 'serial' });

// Helper functions for test data management
async function createTestUser(page, userData = {}) {
  const defaultUser = {
    email: `test-${Date.now()}@example.com`,
    password: 'TestPassword123!',
    firstName: 'Test',
    lastName: 'User'
  };
  
  const user = { ...defaultUser, ...userData };
  
  await page.goto('/register');
  await page.fill('[data-testid="email"]', user.email);
  await page.fill('[data-testid="password"]', user.password);
  await page.fill('[data-testid="confirmPassword"]', user.password);
  await page.fill('[data-testid="firstName"]', user.firstName);
  await page.fill('[data-testid="lastName"]', user.lastName);
  await page.click('[data-testid="register-button"]');
  
  return user;
}

async function loginUser(page, email, password) {
  await page.goto('/login');
  await page.fill('[data-testid="email"]', email);
  await page.fill('[data-testid="password"]', password);
  await page.click('[data-testid="login-button"]');
  await page.waitForURL('/dashboard');
}

// Export helper functions for use in other test files
module.exports = {
  createTestUser,
  loginUser
};