const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: '../reports/e2e-html-report' }],
    ['json', { outputFile: '../reports/e2e-results.json' }],
    ['junit', { outputFile: '../reports/e2e-results.xml' }]
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
  webServer: [
    {
      command: 'npm run start:test-server',
      port: 3000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'cd ../services/sso-system && npm start',
      port: 8201,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'cd ../services/data-bridge && npm start',
      port: 8202,
      reuseExistingServer: !process.env.CI,
    }
  ],
});