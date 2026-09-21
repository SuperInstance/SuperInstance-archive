module.exports = async () => {
  console.log('Tearing down integration test environment...');

  const containers = global.__CONTAINERS__;
  
  if (containers) {
    // Stop all containers
    for (const [name, container] of Object.entries(containers)) {
      try {
        console.log(`Stopping ${name} container...`);
        await container.stop();
        console.log(`${name} container stopped`);
      } catch (error) {
        console.error(`Failed to stop ${name} container:`, error);
      }
    }
  }

  // Clean up environment variables
  delete process.env.MONGODB_URL;
  delete process.env.REDIS_URL;
  delete process.env.ELASTICSEARCH_URL;
  delete process.env.SSO_SYSTEM_PORT;
  delete process.env.SSO_SYSTEM_URL;
  delete process.env.DATA_BRIDGE_PORT;
  delete process.env.DATA_BRIDGE_URL;

  console.log('Integration test environment teardown complete');
};