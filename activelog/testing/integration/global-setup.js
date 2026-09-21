const { GenericContainer, Wait } = require('testcontainers');
const axios = require('axios');

let containers = {};

module.exports = async () => {
  console.log('Setting up integration test environment...');

  try {
    // Start MongoDB container
    console.log('Starting MongoDB container...');
    containers.mongodb = await new GenericContainer('mongo:7.0')
      .withEnvironment({
        MONGO_INITDB_ROOT_USERNAME: 'admin',
        MONGO_INITDB_ROOT_PASSWORD: 'password',
        MONGO_INITDB_DATABASE: 'activelog_test'
      })
      .withExposedPorts(27017)
      .withWaitStrategy(Wait.forLogMessage('Waiting for connections'))
      .start();

    const mongoPort = containers.mongodb.getMappedPort(27017);
    process.env.MONGODB_URL = `mongodb://admin:password@localhost:${mongoPort}/activelog_test?authSource=admin`;
    console.log(`MongoDB started on port ${mongoPort}`);

    // Start Redis container
    console.log('Starting Redis container...');
    containers.redis = await new GenericContainer('redis:7.2-alpine')
      .withExposedPorts(6379)
      .withWaitStrategy(Wait.forLogMessage('Ready to accept connections'))
      .start();

    const redisPort = containers.redis.getMappedPort(6379);
    process.env.REDIS_URL = `redis://localhost:${redisPort}`;
    console.log(`Redis started on port ${redisPort}`);

    // Start Elasticsearch container
    console.log('Starting Elasticsearch container...');
    containers.elasticsearch = await new GenericContainer('elasticsearch:8.11.0')
      .withEnvironment({
        'discovery.type': 'single-node',
        'xpack.security.enabled': 'false',
        'ES_JAVA_OPTS': '-Xms512m -Xmx512m'
      })
      .withExposedPorts(9200)
      .withWaitStrategy(Wait.forHttp('/_cluster/health', 9200))
      .start();

    const esPort = containers.elasticsearch.getMappedPort(9200);
    process.env.ELASTICSEARCH_URL = `http://localhost:${esPort}`;
    console.log(`Elasticsearch started on port ${esPort}`);

    // Start test services
    console.log('Starting test services...');
    
    // Start SSO System (mock)
    process.env.SSO_SYSTEM_PORT = '18201';
    process.env.SSO_SYSTEM_URL = 'http://localhost:18201';
    
    // Start Data Bridge (mock)
    process.env.DATA_BRIDGE_PORT = '18202';
    process.env.DATA_BRIDGE_URL = 'http://localhost:18202';

    // Wait for services to be ready
    await waitForServices();

    // Store container references globally
    global.__CONTAINERS__ = containers;
    
    console.log('Integration test environment setup complete');

  } catch (error) {
    console.error('Failed to setup integration test environment:', error);
    // Cleanup on failure
    await cleanupContainers(containers);
    throw error;
  }
};

async function waitForServices() {
  const services = [
    { name: 'SSO System', url: process.env.SSO_SYSTEM_URL + '/health' },
    { name: 'Data Bridge', url: process.env.DATA_BRIDGE_URL + '/health' },
    { name: 'Elasticsearch', url: process.env.ELASTICSEARCH_URL + '/_cluster/health' }
  ];

  const maxRetries = 30;
  const retryDelay = 2000;

  for (const service of services) {
    console.log(`Waiting for ${service.name}...`);
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        await axios.get(service.url, { timeout: 5000 });
        console.log(`${service.name} is ready`);
        break;
      } catch (error) {
        if (attempt === maxRetries) {
          throw new Error(`${service.name} failed to start after ${maxRetries} attempts`);
        }
        console.log(`${service.name} not ready, attempt ${attempt}/${maxRetries}`);
        await sleep(retryDelay);
      }
    }
  }
}

async function cleanupContainers(containers) {
  console.log('Cleaning up containers...');
  for (const [name, container] of Object.entries(containers)) {
    try {
      await container.stop();
      console.log(`Stopped ${name} container`);
    } catch (error) {
      console.error(`Failed to stop ${name} container:`, error);
    }
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}