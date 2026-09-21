import { getDb } from '../database/init.js';
import { logger } from '../utils/logger.js';
import { NodeSSH } from 'node-ssh';
import axios from 'axios';

export class ProviderManager {
  constructor() {
    this.ssh = new NodeSSH();
    this.heartbeatInterval = null;
  }

  async registerProvider(providerData) {
    const db = getDb();
    
    try {
      const result = await new Promise((resolve, reject) => {
        db.run(`
          INSERT INTO providers (
            university_id, name, type, endpoint, ssh_host, ssh_port,
            ssh_username, ssh_key_path, config_data, total_cpu_cores,
            total_memory_gb, total_storage_gb, available_cpu_cores,
            available_memory_gb, available_storage_gb, status
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `, [
          providerData.university_id, providerData.name, providerData.type,
          providerData.endpoint, providerData.ssh_host, providerData.ssh_port || 22,
          providerData.ssh_username, providerData.ssh_key_path,
          JSON.stringify(providerData.config_data || {}),
          providerData.total_cpu_cores, providerData.total_memory_gb,
          providerData.total_storage_gb, providerData.total_cpu_cores,
          providerData.total_memory_gb, providerData.total_storage_gb, 'active'
        ], function(err) {
          if (err) reject(err);
          else resolve({ id: this.lastID });
        });
      });

      // Test connection
      const connectionTest = await this.testProviderConnection(result.id);
      
      if (!connectionTest.success) {
        await this.updateProviderStatus(result.id, 'error');
        logger.warn(`Provider ${result.id} registered but connection failed: ${connectionTest.error}`);
      }

      logger.info(`Provider registered: ${providerData.name} (ID: ${result.id})`);
      return result.id;
    } catch (error) {
      logger.error('Failed to register provider:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async testProviderConnection(providerId) {
    const provider = await this.getProvider(providerId);
    if (!provider) {
      return { success: false, error: 'Provider not found' };
    }

    try {
      switch (provider.type) {
        case 'slurm':
          return await this.testSlurmConnection(provider);
        case 'kubernetes':
          return await this.testKubernetesConnection(provider);
        case 'docker':
          return await this.testDockerConnection(provider);
        case 'bare_metal':
          return await this.testSSHConnection(provider);
        default:
          return { success: false, error: 'Unsupported provider type' };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async testSlurmConnection(provider) {
    try {
      const connection = await this.connectSSH(provider);
      const result = await connection.execCommand('sinfo --version');
      
      if (result.code === 0) {
        await connection.dispose();
        return { success: true, version: result.stdout.trim() };
      } else {
        await connection.dispose();
        return { success: false, error: result.stderr };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async testKubernetesConnection(provider) {
    try {
      const config = JSON.parse(provider.config_data);
      const response = await axios.get(`${provider.endpoint}/version`, {
        headers: {
          'Authorization': `Bearer ${config.token}`
        },
        timeout: parseInt(process.env.UNIVERSITY_API_TIMEOUT) || 30000
      });
      
      return { success: true, version: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async testDockerConnection(provider) {
    try {
      const response = await axios.get(`${provider.endpoint}/version`, {
        timeout: parseInt(process.env.UNIVERSITY_API_TIMEOUT) || 30000
      });
      
      return { success: true, version: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async testSSHConnection(provider) {
    try {
      const connection = await this.connectSSH(provider);
      const result = await connection.execCommand('uptime');
      
      if (result.code === 0) {
        await connection.dispose();
        return { success: true, uptime: result.stdout.trim() };
      } else {
        await connection.dispose();
        return { success: false, error: result.stderr };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async connectSSH(provider) {
    const connection = new NodeSSH();
    
    const config = {
      host: provider.ssh_host,
      port: provider.ssh_port,
      username: provider.ssh_username,
      readyTimeout: parseInt(process.env.SSH_CONNECTION_TIMEOUT) || 10000
    };

    if (provider.ssh_key_path) {
      config.privateKeyPath = provider.ssh_key_path;
    }

    await connection.connect(config);
    return connection;
  }

  async getProvider(providerId) {
    const db = getDb();
    
    try {
      return await new Promise((resolve, reject) => {
        db.get('SELECT * FROM providers WHERE id = ?', [providerId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });
    } catch (error) {
      logger.error('Failed to get provider:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async getActiveProviders(universityId = null) {
    const db = getDb();
    
    try {
      const query = universityId 
        ? 'SELECT * FROM providers WHERE status = "active" AND university_id = ? ORDER BY reputation_score DESC'
        : 'SELECT * FROM providers WHERE status = "active" ORDER BY reputation_score DESC';
      
      const params = universityId ? [universityId] : [];
      
      return await new Promise((resolve, reject) => {
        db.all(query, params, (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });
    } catch (error) {
      logger.error('Failed to get active providers:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async updateProviderStatus(providerId, status) {
    const db = getDb();
    
    try {
      await new Promise((resolve, reject) => {
        db.run(
          'UPDATE providers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
          [status, providerId],
          function(err) {
            if (err) reject(err);
            else resolve();
          }
        );
      });
      
      logger.info(`Provider ${providerId} status updated to: ${status}`);
    } catch (error) {
      logger.error('Failed to update provider status:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async updateProviderCapacity(providerId, capacityData) {
    const db = getDb();
    
    try {
      await new Promise((resolve, reject) => {
        db.run(`
          UPDATE providers SET 
            available_cpu_cores = ?,
            available_memory_gb = ?,
            available_storage_gb = ?,
            utilization_percent = ?,
            last_heartbeat = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
          WHERE id = ?
        `, [
          capacityData.available_cpu_cores,
          capacityData.available_memory_gb,
          capacityData.available_storage_gb,
          capacityData.utilization_percent,
          providerId
        ], function(err) {
          if (err) reject(err);
          else resolve();
        });
      });

      // Record capacity monitoring data
      await this.recordCapacityMetrics(providerId, capacityData);
      
    } catch (error) {
      logger.error('Failed to update provider capacity:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async recordCapacityMetrics(providerId, capacityData) {
    const db = getDb();
    
    try {
      await new Promise((resolve, reject) => {
        db.run(`
          INSERT INTO capacity_monitoring (
            provider_id, cpu_utilization, memory_utilization,
            storage_utilization, active_jobs, queued_jobs,
            spare_capacity_percent
          ) VALUES (?, ?, ?, ?, ?, ?, ?)
        `, [
          providerId,
          capacityData.cpu_utilization || 0,
          capacityData.memory_utilization || 0,
          capacityData.storage_utilization || 0,
          capacityData.active_jobs || 0,
          capacityData.queued_jobs || 0,
          capacityData.spare_capacity_percent || 0
        ], function(err) {
          if (err) reject(err);
          else resolve();
        });
      });
    } catch (error) {
      logger.error('Failed to record capacity metrics:', error);
    } finally {
      db.close();
    }
  }

  async getProviderCapacity(providerId) {
    const db = getDb();
    
    try {
      return await new Promise((resolve, reject) => {
        db.get(`
          SELECT 
            available_cpu_cores,
            available_memory_gb,
            available_storage_gb,
            utilization_percent,
            last_heartbeat
          FROM providers WHERE id = ?
        `, [providerId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });
    } catch (error) {
      logger.error('Failed to get provider capacity:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async getSpareCapacity(providerId = null) {
    const db = getDb();
    
    try {
      const query = providerId
        ? `SELECT p.*, cm.spare_capacity_percent, cm.timestamp as last_check
           FROM providers p 
           LEFT JOIN capacity_monitoring cm ON p.id = cm.provider_id 
           WHERE p.id = ? AND p.status = 'active'
           ORDER BY cm.timestamp DESC LIMIT 1`
        : `SELECT p.*, cm.spare_capacity_percent, cm.timestamp as last_check
           FROM providers p 
           LEFT JOIN capacity_monitoring cm ON p.id = cm.provider_id 
           WHERE p.status = 'active'
           GROUP BY p.id
           HAVING cm.timestamp = MAX(cm.timestamp)
           ORDER BY cm.spare_capacity_percent DESC`;
      
      const params = providerId ? [providerId] : [];
      
      return await new Promise((resolve, reject) => {
        if (providerId) {
          db.get(query, params, (err, row) => {
            if (err) reject(err);
            else resolve(row);
          });
        } else {
          db.all(query, params, (err, rows) => {
            if (err) reject(err);
            else resolve(rows);
          });
        }
      });
    } catch (error) {
      logger.error('Failed to get spare capacity:', error);
      throw error;
    } finally {
      db.close();
    }
  }

  async startHeartbeatMonitoring() {
    const interval = parseInt(process.env.HEALTH_CHECK_INTERVAL) * 1000 || 30000;
    
    this.heartbeatInterval = setInterval(async () => {
      try {
        const providers = await this.getActiveProviders();
        
        for (const provider of providers) {
          try {
            const connectionTest = await this.testProviderConnection(provider.id);
            
            if (connectionTest.success) {
              await this.updateProviderStatus(provider.id, 'active');
            } else {
              logger.warn(`Provider ${provider.id} heartbeat failed: ${connectionTest.error}`);
              await this.updateProviderStatus(provider.id, 'error');
            }
          } catch (error) {
            logger.error(`Heartbeat check failed for provider ${provider.id}:`, error);
            await this.updateProviderStatus(provider.id, 'error');
          }
        }
      } catch (error) {
        logger.error('Heartbeat monitoring error:', error);
      }
    }, interval);
    
    logger.info('Provider heartbeat monitoring started');
  }

  stopHeartbeatMonitoring() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
      logger.info('Provider heartbeat monitoring stopped');
    }
  }
}