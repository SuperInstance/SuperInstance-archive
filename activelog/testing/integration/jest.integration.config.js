module.exports = {
  displayName: 'Integration Tests',
  testMatch: ['**/integration/**/*.test.js'],
  testEnvironment: 'node',
  setupFilesAfterEnv: ['<rootDir>/integration/setup.js'],
  globalSetup: '<rootDir>/integration/global-setup.js',
  globalTeardown: '<rootDir>/integration/global-teardown.js',
  collectCoverage: true,
  coverageDirectory: '../reports/integration-coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  testTimeout: 30000,
  maxWorkers: 1, // Run integration tests serially
  verbose: true,
  reporters: [
    'default',
    ['jest-junit', {
      outputDirectory: '../reports',
      outputName: 'integration-test-results.xml'
    }],
    ['jest-html-reporter', {
      pageTitle: 'Integration Test Report',
      outputPath: '../reports/integration-report.html'
    }]
  ]
};