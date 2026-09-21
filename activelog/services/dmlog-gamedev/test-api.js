const http = require('http');

// Simple test campaign data
const testCampaign = {
  id: 'test-001',
  title: 'Test Campaign',
  name: 'Basic Adventure',
  description: 'A simple test campaign',
  setting: 'Fantasy',
  theme: 'Adventure',
  genre: 'RPG',
  sessions: [],
  characters: [
    {
      id: 'char-001',
      name: 'Test Hero',
      race: 'Human',
      class: 'Fighter',
      level: 1,
      type: 'player',
      personality: {
        traits: ['Brave'],
        ideals: ['Justice'],
        bonds: ['Family'],
        flaws: ['Reckless'],
        alignment: 'Good',
        temperament: 'Bold',
        speechPattern: 'Direct',
        quirks: ['Taps sword']
      },
      backstory: 'A simple hero',
      goals: ['Save the day'],
      relationships: [],
      stats: {
        attributes: { str: 15, dex: 12, con: 14, int: 10, wis: 13, cha: 11 },
        skills: {},
        saves: {},
        hitPoints: { current: 10, maximum: 10 },
        armorClass: 16,
        speed: 30,
        proficiencyBonus: 2
      },
      abilities: [],
      inventory: [],
      progression: [],
      voiceLines: ['For justice!'],
      characterArc: {
        phases: [],
        growth: [],
        conflicts: [],
        resolution: 'Becomes hero'
      }
    }
  ],
  npcs: [],
  locations: [],
  quests: [],
  items: [],
  encounters: [],
  worldbuilding: {
    history: [],
    politics: [],
    religion: [],
    culture: [],
    economy: [],
    geography: []
  },
  mechanics: {
    houseRules: [],
    customSystems: [],
    modifications: [],
    balanceChanges: []
  },
  notes: [],
  assets: []
};

async function testServiceEndpoint(path, data = null) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'localhost',
      port: 3006,
      path: path,
      method: data ? 'POST' : 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => {
        body += chunk;
      });
      res.on('end', () => {
        try {
          const response = JSON.parse(body);
          resolve({ status: res.statusCode, data: response });
        } catch (e) {
          resolve({ status: res.statusCode, data: body });
        }
      });
    });

    req.on('error', (err) => {
      reject(err);
    });

    if (data) {
      req.write(JSON.stringify(data));
    }
    req.end();
  });
}

async function runTests() {
  console.log('🧪 Testing DMLog GameDev Service API\n');

  try {
    // Test 1: Health check
    console.log('1. Testing health endpoint...');
    const healthResponse = await testServiceEndpoint('/health');
    if (healthResponse.status === 200) {
      console.log('✅ Health check passed');
      console.log('   Response:', healthResponse.data);
    } else {
      console.log('❌ Health check failed:', healthResponse.status);
      return;
    }

    // Test 2: Generate monetization plan
    console.log('\n2. Testing monetization plan generation...');
    const monetizationData = {
      campaign: testCampaign,
      options: {
        primary_model: 'freemium',
        target_revenue: 25000,
        target_demographics: ['18-35', 'gamers'],
        risk_tolerance: 'moderate',
        platform_focus: ['pc', 'mobile'],
        compliance_regions: ['us', 'eu'],
        ethical_constraints: [],
        competitive_positioning: 'mid_market'
      }
    };

    const monetizationResponse = await testServiceEndpoint('/generate/monetization-plan', monetizationData);
    if (monetizationResponse.status === 200 && monetizationResponse.data.success) {
      console.log('✅ Monetization plan generation passed');
      console.log('   Plan ID:', monetizationResponse.data.plan?.id || 'Generated');
    } else {
      console.log('❌ Monetization plan generation failed');
      console.log('   Status:', monetizationResponse.status);
      console.log('   Error:', monetizationResponse.data);
    }

    // Test 3: List assets
    console.log('\n3. Testing assets list endpoint...');
    const assetsResponse = await testServiceEndpoint('/assets/list');
    if (assetsResponse.status === 200) {
      console.log('✅ Assets list passed');
      console.log('   Assets:', assetsResponse.data.assets?.length || 0, 'found');
    } else {
      console.log('❌ Assets list failed:', assetsResponse.status);
    }

    console.log('\n🎉 API tests completed!');

  } catch (error) {
    console.error('❌ Test execution failed:', error.message);
    if (error.code === 'ECONNREFUSED') {
      console.log('\n💡 Note: Make sure the DMLog GameDev service is running on port 3006');
      console.log('   Try running: npm run dev');
    }
  }
}

// Start the test
runTests();