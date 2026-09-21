const { Pact } = require('@pact-foundation/pact');
const path = require('path');

// Consumer configurations
const personalLogConsumerConfig = {
  consumer: 'PersonalLog',
  provider: 'SSOSystem',
  port: 1234,
  log: path.resolve(process.cwd(), '../reports/pact-logs', 'personal-log-sso.log'),
  dir: path.resolve(process.cwd(), '../reports/pacts'),
  spec: 2,
  pactfileWriteMode: 'overwrite',
  logLevel: 'INFO'
};

const businessLogConsumerConfig = {
  consumer: 'BusinessLog',
  provider: 'DataBridge',
  port: 1235,
  log: path.resolve(process.cwd(), '../reports/pact-logs', 'business-log-databridge.log'),
  dir: path.resolve(process.cwd(), '../reports/pacts'),
  spec: 2,
  pactfileWriteMode: 'overwrite',
  logLevel: 'INFO'
};

const dataBridgeConsumerConfig = {
  consumer: 'DataBridge',
  provider: 'SSOSystem',
  port: 1236,
  log: path.resolve(process.cwd(), '../reports/pact-logs', 'databridge-sso.log'),
  dir: path.resolve(process.cwd(), '../reports/pacts'),
  spec: 2,
  pactfileWriteMode: 'overwrite',
  logLevel: 'INFO'
};

// Provider verification configurations
const ssoProviderConfig = {
  providerBaseUrl: process.env.SSO_PROVIDER_URL || 'http://localhost:8201',
  pactBrokerUrl: process.env.PACT_BROKER_URL,
  pactBrokerUsername: process.env.PACT_BROKER_USERNAME,
  pactBrokerPassword: process.env.PACT_BROKER_PASSWORD,
  provider: 'SSOSystem',
  publishVerificationResult: process.env.CI === 'true',
  providerVersion: process.env.GIT_COMMIT || '1.0.0',
  logLevel: 'INFO'
};

const dataBridgeProviderConfig = {
  providerBaseUrl: process.env.DATA_BRIDGE_PROVIDER_URL || 'http://localhost:8202',
  pactBrokerUrl: process.env.PACT_BROKER_URL,
  pactBrokerUsername: process.env.PACT_BROKER_USERNAME,
  pactBrokerPassword: process.env.PACT_BROKER_PASSWORD,
  provider: 'DataBridge',
  publishVerificationResult: process.env.CI === 'true',
  providerVersion: process.env.GIT_COMMIT || '1.0.0',
  logLevel: 'INFO'
};

module.exports = {
  personalLogConsumerConfig,
  businessLogConsumerConfig,
  dataBridgeConsumerConfig,
  ssoProviderConfig,
  dataBridgeProviderConfig,
  
  // Helper function to create Pact instances
  createPersonalLogSSOPact: () => new Pact(personalLogConsumerConfig),
  createBusinessLogDataBridgePact: () => new Pact(businessLogConsumerConfig),
  createDataBridgeSSOPact: () => new Pact(dataBridgeConsumerConfig)
};