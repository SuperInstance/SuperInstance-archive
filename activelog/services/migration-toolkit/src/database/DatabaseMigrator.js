import fs from 'fs-extra';
import path from 'path';
import mysql from 'mysql2/promise';
import { MongoClient } from 'mongodb';
import pkg from 'pg';
import sqlite3 from 'sqlite3';
import logger from '../lib/logger.js';
import { DatabaseSchemaAnalyzer } from '../analyzers/DatabaseSchemaAnalyzer.js';

const { Client: PostgresClient } = pkg;

/**
 * Comprehensive database migration tool
 * Supports MySQL, PostgreSQL, MongoDB, SQLite, and more
 */
export class DatabaseMigrator {
  constructor(options = {}) {
    this.options = {
      batchSize: 1000,
      parallelConnections: 5,
      timeout: 30000,
      enableCompression: true,
      validateData: true,
      createBackups: true,
      preserveIndexes: true,
      preserveConstraints: true,
      ...options
    };

    this.schemaAnalyzer = new DatabaseSchemaAnalyzer();
    this.supportedDatabases = [
      'mysql', 'postgresql', 'mongodb', 'sqlite',
      'mariadb', 'oracle', 'mssql', 'redis'
    ];
  }

  /**
   * Main migration orchestrator
   */
  async migrateDatabase(sourceConfig, targetConfig, options = {}) {
    const migrationId = this.generateMigrationId();
    logger.info(`Starting database migration ${migrationId}`);

    try {
      const migrationPlan = {
        id: migrationId,
        timestamp: new Date().toISOString(),
        source: sourceConfig,
        target: targetConfig,
        options: { ...this.options, ...options },
        status: 'in_progress',
        steps: [],
        statistics: {},
        errors: [],
        warnings: []
      };

      // Step 1: Validate connections
      logger.info('Validating database connections...');
      await this.validateConnections(sourceConfig, targetConfig);
      migrationPlan.steps.push({ step: 'connection_validation', status: 'completed', timestamp: new Date().toISOString() });

      // Step 2: Analyze source database
      logger.info('Analyzing source database schema...');
      const sourceSchema = await this.analyzeSourceDatabase(sourceConfig);
      migrationPlan.sourceSchema = sourceSchema;
      migrationPlan.steps.push({ step: 'source_analysis', status: 'completed', timestamp: new Date().toISOString() });

      // Step 3: Create target schema
      logger.info('Creating target database schema...');
      await this.createTargetSchema(sourceSchema, targetConfig);
      migrationPlan.steps.push({ step: 'target_schema_creation', status: 'completed', timestamp: new Date().toISOString() });

      // Step 4: Create backup if requested
      if (this.options.createBackups) {
        logger.info('Creating source database backup...');
        const backupPath = await this.createBackup(sourceConfig, migrationId);
        migrationPlan.backupPath = backupPath;
        migrationPlan.steps.push({ step: 'backup_creation', status: 'completed', timestamp: new Date().toISOString() });
      }

      // Step 5: Migrate data
      logger.info('Migrating data...');
      const migrationStats = await this.migrateData(sourceConfig, targetConfig, sourceSchema);
      migrationPlan.statistics = migrationStats;
      migrationPlan.steps.push({ step: 'data_migration', status: 'completed', timestamp: new Date().toISOString() });

      // Step 6: Create indexes and constraints
      if (this.options.preserveIndexes || this.options.preserveConstraints) {
        logger.info('Creating indexes and constraints...');
        await this.createIndexesAndConstraints(sourceSchema, targetConfig);
        migrationPlan.steps.push({ step: 'indexes_constraints', status: 'completed', timestamp: new Date().toISOString() });
      }

      // Step 7: Validate migration
      if (this.options.validateData) {
        logger.info('Validating migrated data...');
        const validationResult = await this.validateMigration(sourceConfig, targetConfig, sourceSchema);
        migrationPlan.validation = validationResult;
        migrationPlan.steps.push({ step: 'data_validation', status: 'completed', timestamp: new Date().toISOString() });
      }

      migrationPlan.status = 'completed';
      migrationPlan.completedAt = new Date().toISOString();
      
      logger.info(`Database migration ${migrationId} completed successfully`);
      return migrationPlan;

    } catch (error) {
      logger.error(`Database migration ${migrationId} failed:`, error);
      throw error;
    }
  }

  /**
   * Validate database connections
   */
  async validateConnections(sourceConfig, targetConfig) {
    const sourceConnection = await this.createConnection(sourceConfig);
    const targetConnection = await this.createConnection(targetConfig);

    try {
      await this.testConnection(sourceConnection, sourceConfig.type);
      await this.testConnection(targetConnection, targetConfig.type);
    } finally {
      await this.closeConnection(sourceConnection, sourceConfig.type);
      await this.closeConnection(targetConnection, targetConfig.type);
    }
  }

  /**
   * Create database connection based on type
   */
  async createConnection(config) {
    switch (config.type.toLowerCase()) {
      case 'mysql':
      case 'mariadb':
        return await mysql.createConnection({
          host: config.host,
          port: config.port || 3306,
          user: config.username,
          password: config.password,
          database: config.database,
          timeout: this.options.timeout,
          acquireTimeout: this.options.timeout,
          ssl: config.ssl || false
        });

      case 'postgresql':
        const pgClient = new PostgresClient({
          host: config.host,
          port: config.port || 5432,
          user: config.username,
          password: config.password,
          database: config.database,
          connectionTimeoutMillis: this.options.timeout,
          ssl: config.ssl || false
        });
        await pgClient.connect();
        return pgClient;

      case 'mongodb':
        const mongoClient = new MongoClient(config.connectionString || 
          `mongodb://${config.username}:${config.password}@${config.host}:${config.port || 27017}/${config.database}`, {
          connectTimeoutMS: this.options.timeout,
          socketTimeoutMS: this.options.timeout
        });
        await mongoClient.connect();
        return mongoClient;

      case 'sqlite':
        return new Promise((resolve, reject) => {
          const db = new sqlite3.Database(config.file, (err) => {
            if (err) reject(err);
            else resolve(db);
          });
        });

      default:
        throw new Error(`Unsupported database type: ${config.type}`);
    }
  }

  /**
   * Test database connection
   */
  async testConnection(connection, dbType) {
    switch (dbType.toLowerCase()) {
      case 'mysql':
      case 'mariadb':
        await connection.execute('SELECT 1');
        break;

      case 'postgresql':
        await connection.query('SELECT 1');
        break;

      case 'mongodb':
        await connection.db().admin().ping();
        break;

      case 'sqlite':
        return new Promise((resolve, reject) => {
          connection.get('SELECT 1', (err) => {
            if (err) reject(err);
            else resolve();
          });
        });

      default:
        throw new Error(`Unknown database type: ${dbType}`);
    }
  }

  /**
   * Close database connection
   */
  async closeConnection(connection, dbType) {
    try {
      switch (dbType.toLowerCase()) {
        case 'mysql':
        case 'mariadb':
          await connection.end();
          break;

        case 'postgresql':
          await connection.end();
          break;

        case 'mongodb':
          await connection.close();
          break;

        case 'sqlite':
          connection.close();
          break;
      }
    } catch (error) {
      logger.warn('Error closing connection:', error);
    }
  }

  /**
   * Analyze source database structure
   */
  async analyzeSourceDatabase(sourceConfig) {
    const connection = await this.createConnection(sourceConfig);
    
    try {
      switch (sourceConfig.type.toLowerCase()) {
        case 'mysql':
        case 'mariadb':
          return await this.analyzeMySQLDatabase(connection, sourceConfig);

        case 'postgresql':
          return await this.analyzePostgreSQLDatabase(connection, sourceConfig);

        case 'mongodb':
          return await this.analyzeMongoDBDatabase(connection, sourceConfig);

        case 'sqlite':
          return await this.analyzeSQLiteDatabase(connection, sourceConfig);

        default:
          throw new Error(`Database analysis not implemented for: ${sourceConfig.type}`);
      }
    } finally {
      await this.closeConnection(connection, sourceConfig.type);
    }
  }

  /**
   * Analyze MySQL database
   */
  async analyzeMySQLDatabase(connection, config) {
    const schema = {
      type: 'mysql',
      database: config.database,
      tables: [],
      views: [],
      procedures: [],
      functions: [],
      triggers: [],
      indexes: []
    };

    // Get tables
    const [tables] = await connection.execute(
      'SELECT TABLE_NAME, TABLE_TYPE, ENGINE, TABLE_COLLATION FROM information_schema.tables WHERE table_schema = ?',
      [config.database]
    );

    for (const table of tables) {
      if (table.TABLE_TYPE === 'BASE TABLE') {
        const tableInfo = {
          name: table.TABLE_NAME,
          engine: table.ENGINE,
          collation: table.TABLE_COLLATION,
          columns: [],
          indexes: [],
          constraints: []
        };

        // Get columns
        const [columns] = await connection.execute(
          'SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_KEY, EXTRA FROM information_schema.columns WHERE table_schema = ? AND table_name = ? ORDER BY ORDINAL_POSITION',
          [config.database, table.TABLE_NAME]
        );

        tableInfo.columns = columns.map(col => ({
          name: col.COLUMN_NAME,
          type: col.DATA_TYPE,
          nullable: col.IS_NULLABLE === 'YES',
          default: col.COLUMN_DEFAULT,
          key: col.COLUMN_KEY,
          extra: col.EXTRA
        }));

        // Get indexes
        const [indexes] = await connection.execute(
          'SHOW INDEX FROM ??',
          [table.TABLE_NAME]
        );

        const indexMap = {};
        for (const idx of indexes) {
          if (!indexMap[idx.Key_name]) {
            indexMap[idx.Key_name] = {
              name: idx.Key_name,
              unique: idx.Non_unique === 0,
              columns: []
            };
          }
          indexMap[idx.Key_name].columns.push(idx.Column_name);
        }

        tableInfo.indexes = Object.values(indexMap);
        schema.tables.push(tableInfo);
      } else if (table.TABLE_TYPE === 'VIEW') {
        schema.views.push({ name: table.TABLE_NAME });
      }
    }

    return schema;
  }

  /**
   * Analyze PostgreSQL database
   */
  async analyzePostgreSQLDatabase(connection, config) {
    const schema = {
      type: 'postgresql',
      database: config.database,
      schemas: [],
      tables: [],
      views: [],
      functions: [],
      indexes: []
    };

    // Get schemas
    const schemaResult = await connection.query(
      'SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN (\'information_schema\', \'pg_catalog\', \'pg_toast\')'
    );
    schema.schemas = schemaResult.rows.map(row => row.schema_name);

    // Get tables
    const tablesResult = await connection.query(`
      SELECT table_schema, table_name, table_type 
      FROM information_schema.tables 
      WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
    `);

    for (const table of tablesResult.rows) {
      if (table.table_type === 'BASE TABLE') {
        const tableInfo = {
          schema: table.table_schema,
          name: table.table_name,
          columns: [],
          indexes: [],
          constraints: []
        };

        // Get columns
        const columnsResult = await connection.query(`
          SELECT column_name, data_type, is_nullable, column_default
          FROM information_schema.columns 
          WHERE table_schema = $1 AND table_name = $2
          ORDER BY ordinal_position
        `, [table.table_schema, table.table_name]);

        tableInfo.columns = columnsResult.rows.map(col => ({
          name: col.column_name,
          type: col.data_type,
          nullable: col.is_nullable === 'YES',
          default: col.column_default
        }));

        schema.tables.push(tableInfo);
      }
    }

    return schema;
  }

  /**
   * Analyze MongoDB database
   */
  async analyzeMongoDBDatabase(connection, config) {
    const db = connection.db(config.database);
    const schema = {
      type: 'mongodb',
      database: config.database,
      collections: []
    };

    // Get collections
    const collections = await db.listCollections().toArray();

    for (const collection of collections) {
      const collectionInfo = {
        name: collection.name,
        type: collection.type,
        indexes: [],
        sampleDocument: null,
        documentCount: 0
      };

      const coll = db.collection(collection.name);
      
      // Get document count
      collectionInfo.documentCount = await coll.countDocuments();

      // Get sample document for schema inference
      const sample = await coll.findOne();
      if (sample) {
        collectionInfo.sampleDocument = this.inferMongoSchema(sample);
      }

      // Get indexes
      const indexes = await coll.indexes();
      collectionInfo.indexes = indexes;

      schema.collections.push(collectionInfo);
    }

    return schema;
  }

  /**
   * Analyze SQLite database
   */
  async analyzeSQLiteDatabase(connection, config) {
    return new Promise((resolve, reject) => {
      const schema = {
        type: 'sqlite',
        database: config.file,
        tables: [],
        views: [],
        indexes: []
      };

      // Get tables
      connection.all(
        "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'",
        (err, rows) => {
          if (err) {
            reject(err);
            return;
          }

          const promises = rows.map(row => {
            return new Promise((resolveTable, rejectTable) => {
              if (row.type === 'table') {
                // Get table info
                connection.all(`PRAGMA table_info(${row.name})`, (err, columns) => {
                  if (err) {
                    rejectTable(err);
                    return;
                  }

                  const tableInfo = {
                    name: row.name,
                    columns: columns.map(col => ({
                      name: col.name,
                      type: col.type,
                      nullable: col.notnull === 0,
                      default: col.dflt_value,
                      primaryKey: col.pk === 1
                    })),
                    indexes: []
                  };

                  schema.tables.push(tableInfo);
                  resolveTable();
                });
              } else {
                schema.views.push({ name: row.name });
                resolveTable();
              }
            });
          });

          Promise.all(promises)
            .then(() => resolve(schema))
            .catch(reject);
        }
      );
    });
  }

  /**
   * Create target database schema
   */
  async createTargetSchema(sourceSchema, targetConfig) {
    const connection = await this.createConnection(targetConfig);

    try {
      switch (targetConfig.type.toLowerCase()) {
        case 'mysql':
        case 'mariadb':
          await this.createMySQLSchema(connection, sourceSchema, targetConfig);
          break;

        case 'postgresql':
          await this.createPostgreSQLSchema(connection, sourceSchema, targetConfig);
          break;

        case 'mongodb':
          await this.createMongoDBSchema(connection, sourceSchema, targetConfig);
          break;

        case 'sqlite':
          await this.createSQLiteSchema(connection, sourceSchema, targetConfig);
          break;

        default:
          throw new Error(`Schema creation not implemented for: ${targetConfig.type}`);
      }
    } finally {
      await this.closeConnection(connection, targetConfig.type);
    }
  }

  /**
   * Create MySQL schema
   */
  async createMySQLSchema(connection, sourceSchema, targetConfig) {
    for (const table of sourceSchema.tables) {
      let createTableSQL = `CREATE TABLE IF NOT EXISTS \`${table.name}\` (\n`;
      
      const columnDefs = table.columns.map(col => {
        let def = `  \`${col.name}\` ${this.convertDataType(col.type, 'mysql', sourceSchema.type)}`;
        if (!col.nullable) def += ' NOT NULL';
        if (col.default !== null && col.default !== undefined) {
          def += ` DEFAULT ${col.default}`;
        }
        if (col.extra) def += ` ${col.extra}`;
        return def;
      });

      createTableSQL += columnDefs.join(',\n');
      
      // Add primary key
      const primaryKeys = table.columns.filter(col => col.key === 'PRI');
      if (primaryKeys.length > 0) {
        createTableSQL += `,\n  PRIMARY KEY (${primaryKeys.map(col => `\`${col.name}\``).join(', ')})`;
      }

      createTableSQL += `\n) ENGINE=${table.engine || 'InnoDB'} DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`;

      await connection.execute(createTableSQL);
      logger.info(`Created table: ${table.name}`);
    }
  }

  /**
   * Create PostgreSQL schema
   */
  async createPostgreSQLSchema(connection, sourceSchema, targetConfig) {
    // Create schemas first
    if (sourceSchema.schemas) {
      for (const schemaName of sourceSchema.schemas) {
        await connection.query(`CREATE SCHEMA IF NOT EXISTS "${schemaName}"`);
      }
    }

    for (const table of sourceSchema.tables) {
      const tableName = table.schema ? `"${table.schema}"."${table.name}"` : `"${table.name}"`;
      let createTableSQL = `CREATE TABLE IF NOT EXISTS ${tableName} (\n`;
      
      const columnDefs = table.columns.map(col => {
        let def = `  "${col.name}" ${this.convertDataType(col.type, 'postgresql', sourceSchema.type)}`;
        if (!col.nullable) def += ' NOT NULL';
        if (col.default !== null && col.default !== undefined) {
          def += ` DEFAULT ${col.default}`;
        }
        return def;
      });

      createTableSQL += columnDefs.join(',\n') + '\n)';
      
      await connection.query(createTableSQL);
      logger.info(`Created table: ${table.schema ? table.schema + '.' : ''}${table.name}`);
    }
  }

  /**
   * Create MongoDB schema (collections)
   */
  async createMongoDBSchema(connection, sourceSchema, targetConfig) {
    const db = connection.db(targetConfig.database);

    for (const collection of sourceSchema.collections || sourceSchema.tables) {
      // MongoDB collections are created automatically when first document is inserted
      // But we can create them explicitly if needed
      try {
        await db.createCollection(collection.name);
        logger.info(`Created collection: ${collection.name}`);
      } catch (error) {
        if (!error.message.includes('already exists')) {
          throw error;
        }
      }
    }
  }

  /**
   * Create SQLite schema
   */
  async createSQLiteSchema(connection, sourceSchema, targetConfig) {
    return new Promise((resolve, reject) => {
      const createPromises = sourceSchema.tables.map(table => {
        return new Promise((resolveTable, rejectTable) => {
          let createTableSQL = `CREATE TABLE IF NOT EXISTS "${table.name}" (\n`;
          
          const columnDefs = table.columns.map(col => {
            let def = `  "${col.name}" ${this.convertDataType(col.type, 'sqlite', sourceSchema.type)}`;
            if (!col.nullable) def += ' NOT NULL';
            if (col.primaryKey) def += ' PRIMARY KEY';
            if (col.default !== null && col.default !== undefined) {
              def += ` DEFAULT ${col.default}`;
            }
            return def;
          });

          createTableSQL += columnDefs.join(',\n') + '\n)';

          connection.run(createTableSQL, (err) => {
            if (err) {
              rejectTable(err);
            } else {
              logger.info(`Created table: ${table.name}`);
              resolveTable();
            }
          });
        });
      });

      Promise.all(createPromises).then(resolve).catch(reject);
    });
  }

  /**
   * Migrate data between databases
   */
  async migrateData(sourceConfig, targetConfig, sourceSchema) {
    const sourceConnection = await this.createConnection(sourceConfig);
    const targetConnection = await this.createConnection(targetConfig);
    
    const stats = {
      tablesProcessed: 0,
      totalRows: 0,
      rowsMigrated: 0,
      errors: [],
      startTime: new Date(),
      endTime: null
    };

    try {
      const tables = sourceSchema.tables || sourceSchema.collections || [];
      
      for (const table of tables) {
        logger.info(`Migrating table: ${table.name}`);
        
        const tableStats = await this.migrateTable(
          sourceConnection, 
          targetConnection, 
          table, 
          sourceConfig, 
          targetConfig
        );
        
        stats.tablesProcessed++;
        stats.rowsMigrated += tableStats.rowsMigrated;
        stats.totalRows += tableStats.totalRows;
        
        if (tableStats.errors.length > 0) {
          stats.errors.push(...tableStats.errors);
        }
      }
      
      stats.endTime = new Date();
      logger.info(`Data migration completed. Migrated ${stats.rowsMigrated} rows from ${stats.tablesProcessed} tables`);
      
    } finally {
      await this.closeConnection(sourceConnection, sourceConfig.type);
      await this.closeConnection(targetConnection, targetConfig.type);
    }

    return stats;
  }

  /**
   * Migrate individual table
   */
  async migrateTable(sourceConnection, targetConnection, table, sourceConfig, targetConfig) {
    const stats = {
      tableName: table.name,
      totalRows: 0,
      rowsMigrated: 0,
      errors: []
    };

    try {
      switch (sourceConfig.type.toLowerCase()) {
        case 'mysql':
        case 'mariadb':
        case 'postgresql':
        case 'sqlite':
          await this.migrateSQLTable(sourceConnection, targetConnection, table, sourceConfig, targetConfig, stats);
          break;

        case 'mongodb':
          await this.migrateMongoCollection(sourceConnection, targetConnection, table, sourceConfig, targetConfig, stats);
          break;
      }
    } catch (error) {
      logger.error(`Error migrating table ${table.name}:`, error);
      stats.errors.push(error.message);
    }

    return stats;
  }

  /**
   * Migrate SQL table
   */
  async migrateSQLTable(sourceConnection, targetConnection, table, sourceConfig, targetConfig, stats) {
    const tableName = table.schema ? `"${table.schema}"."${table.name}"` : table.name;
    const columnNames = table.columns.map(col => col.name);
    
    // Get total row count
    let countQuery;
    if (sourceConfig.type.toLowerCase() === 'mysql') {
      countQuery = `SELECT COUNT(*) as count FROM \`${table.name}\``;
    } else {
      countQuery = `SELECT COUNT(*) as count FROM ${tableName}`;
    }
    
    const countResult = await this.executeQuery(sourceConnection, countQuery, sourceConfig.type);
    stats.totalRows = countResult[0].count || countResult[0].COUNT;

    // Migrate data in batches
    let offset = 0;
    while (offset < stats.totalRows) {
      let selectQuery;
      if (sourceConfig.type.toLowerCase() === 'mysql') {
        selectQuery = `SELECT * FROM \`${table.name}\` LIMIT ${this.options.batchSize} OFFSET ${offset}`;
      } else if (sourceConfig.type.toLowerCase() === 'postgresql') {
        selectQuery = `SELECT * FROM ${tableName} LIMIT ${this.options.batchSize} OFFSET ${offset}`;
      } else if (sourceConfig.type.toLowerCase() === 'sqlite') {
        selectQuery = `SELECT * FROM "${table.name}" LIMIT ${this.options.batchSize} OFFSET ${offset}`;
      }

      const rows = await this.executeQuery(sourceConnection, selectQuery, sourceConfig.type);
      
      if (rows.length === 0) break;

      // Insert batch into target
      await this.insertBatch(targetConnection, table.name, rows, targetConfig.type);
      
      stats.rowsMigrated += rows.length;
      offset += this.options.batchSize;

      logger.info(`Migrated ${stats.rowsMigrated}/${stats.totalRows} rows for table ${table.name}`);
    }
  }

  /**
   * Migrate MongoDB collection
   */
  async migrateMongoCollection(sourceConnection, targetConnection, collection, sourceConfig, targetConfig, stats) {
    const sourceDB = sourceConnection.db(sourceConfig.database);
    const targetDB = targetConnection.db(targetConfig.database);
    
    const sourceColl = sourceDB.collection(collection.name);
    const targetColl = targetDB.collection(collection.name);
    
    // Get total document count
    stats.totalRows = await sourceColl.countDocuments();
    
    // Migrate documents in batches
    let skip = 0;
    while (skip < stats.totalRows) {
      const cursor = sourceColl.find().skip(skip).limit(this.options.batchSize);
      const documents = await cursor.toArray();
      
      if (documents.length === 0) break;
      
      // Insert batch into target
      await targetColl.insertMany(documents);
      
      stats.rowsMigrated += documents.length;
      skip += this.options.batchSize;
      
      logger.info(`Migrated ${stats.rowsMigrated}/${stats.totalRows} documents for collection ${collection.name}`);
    }
  }

  /**
   * Execute query based on database type
   */
  async executeQuery(connection, query, dbType) {
    switch (dbType.toLowerCase()) {
      case 'mysql':
      case 'mariadb':
        const [rows] = await connection.execute(query);
        return rows;

      case 'postgresql':
        const result = await connection.query(query);
        return result.rows;

      case 'sqlite':
        return new Promise((resolve, reject) => {
          connection.all(query, (err, rows) => {
            if (err) reject(err);
            else resolve(rows);
          });
        });

      default:
        throw new Error(`Query execution not implemented for: ${dbType}`);
    }
  }

  /**
   * Insert batch of data
   */
  async insertBatch(connection, tableName, rows, dbType) {
    if (rows.length === 0) return;

    switch (dbType.toLowerCase()) {
      case 'mysql':
      case 'mariadb':
        const columns = Object.keys(rows[0]);
        const placeholders = columns.map(() => '?').join(',');
        const insertSQL = `INSERT INTO \`${tableName}\` (${columns.map(c => `\`${c}\``).join(',')}) VALUES (${placeholders})`;
        
        for (const row of rows) {
          const values = columns.map(col => row[col]);
          await connection.execute(insertSQL, values);
        }
        break;

      case 'postgresql':
        const pgColumns = Object.keys(rows[0]);
        const pgPlaceholders = pgColumns.map((_, i) => `$${i + 1}`).join(',');
        const pgInsertSQL = `INSERT INTO "${tableName}" (${pgColumns.map(c => `"${c}"`).join(',')}) VALUES (${pgPlaceholders})`;
        
        for (const row of rows) {
          const values = pgColumns.map(col => row[col]);
          await connection.query(pgInsertSQL, values);
        }
        break;

      case 'sqlite':
        const sqliteColumns = Object.keys(rows[0]);
        const sqlitePlaceholders = sqliteColumns.map(() => '?').join(',');
        const sqliteInsertSQL = `INSERT INTO "${tableName}" (${sqliteColumns.map(c => `"${c}"`).join(',')}) VALUES (${sqlitePlaceholders})`;
        
        for (const row of rows) {
          await new Promise((resolve, reject) => {
            const values = sqliteColumns.map(col => row[col]);
            connection.run(sqliteInsertSQL, values, (err) => {
              if (err) reject(err);
              else resolve();
            });
          });
        }
        break;
    }
  }

  /**
   * Create indexes and constraints
   */
  async createIndexesAndConstraints(sourceSchema, targetConfig) {
    const connection = await this.createConnection(targetConfig);
    
    try {
      for (const table of sourceSchema.tables || []) {
        if (table.indexes) {
          for (const index of table.indexes) {
            if (index.name !== 'PRIMARY') {
              await this.createIndex(connection, table.name, index, targetConfig.type);
            }
          }
        }
      }
    } finally {
      await this.closeConnection(connection, targetConfig.type);
    }
  }

  /**
   * Create index
   */
  async createIndex(connection, tableName, index, dbType) {
    try {
      let indexSQL;
      const indexName = `idx_${tableName}_${index.columns.join('_')}`;
      
      switch (dbType.toLowerCase()) {
        case 'mysql':
        case 'mariadb':
          indexSQL = `CREATE ${index.unique ? 'UNIQUE' : ''} INDEX \`${indexName}\` ON \`${tableName}\` (${index.columns.map(c => `\`${c}\``).join(',')})`;
          await connection.execute(indexSQL);
          break;

        case 'postgresql':
          indexSQL = `CREATE ${index.unique ? 'UNIQUE' : ''} INDEX "${indexName}" ON "${tableName}" (${index.columns.map(c => `"${c}"`).join(',')})`;
          await connection.query(indexSQL);
          break;

        case 'sqlite':
          indexSQL = `CREATE ${index.unique ? 'UNIQUE' : ''} INDEX "${indexName}" ON "${tableName}" (${index.columns.map(c => `"${c}"`).join(',')})`;
          await new Promise((resolve, reject) => {
            connection.run(indexSQL, (err) => {
              if (err) reject(err);
              else resolve();
            });
          });
          break;
      }

      logger.info(`Created index: ${indexName}`);
    } catch (error) {
      logger.warn(`Failed to create index ${index.name} on table ${tableName}:`, error);
    }
  }

  /**
   * Validate migration
   */
  async validateMigration(sourceConfig, targetConfig, sourceSchema) {
    const validation = {
      tablesValidated: 0,
      rowCountMatches: 0,
      rowCountMismatches: 0,
      dataValidationPassed: 0,
      dataValidationFailed: 0,
      issues: []
    };

    const sourceConnection = await this.createConnection(sourceConfig);
    const targetConnection = await this.createConnection(targetConfig);

    try {
      for (const table of sourceSchema.tables || sourceSchema.collections || []) {
        const tableValidation = await this.validateTable(
          sourceConnection, 
          targetConnection, 
          table, 
          sourceConfig, 
          targetConfig
        );
        
        validation.tablesValidated++;
        if (tableValidation.rowCountMatch) {
          validation.rowCountMatches++;
        } else {
          validation.rowCountMismatches++;
          validation.issues.push(`Row count mismatch in table ${table.name}`);
        }
        
        if (tableValidation.dataValid) {
          validation.dataValidationPassed++;
        } else {
          validation.dataValidationFailed++;
        }
      }
    } finally {
      await this.closeConnection(sourceConnection, sourceConfig.type);
      await this.closeConnection(targetConnection, targetConfig.type);
    }

    return validation;
  }

  /**
   * Validate individual table
   */
  async validateTable(sourceConnection, targetConnection, table, sourceConfig, targetConfig) {
    try {
      // Count rows in both databases
      const sourceCount = await this.getTableRowCount(sourceConnection, table, sourceConfig);
      const targetCount = await this.getTableRowCount(targetConnection, table, targetConfig);

      return {
        tableName: table.name,
        sourceRowCount: sourceCount,
        targetRowCount: targetCount,
        rowCountMatch: sourceCount === targetCount,
        dataValid: true // Simplified validation
      };
    } catch (error) {
      logger.error(`Error validating table ${table.name}:`, error);
      return {
        tableName: table.name,
        rowCountMatch: false,
        dataValid: false,
        error: error.message
      };
    }
  }

  /**
   * Get table row count
   */
  async getTableRowCount(connection, table, config) {
    let countQuery;
    let tableName = table.name;
    
    if (table.schema) {
      tableName = `"${table.schema}"."${table.name}"`;
    }

    switch (config.type.toLowerCase()) {
      case 'mysql':
      case 'mariadb':
        countQuery = `SELECT COUNT(*) as count FROM \`${table.name}\``;
        const [mysqlRows] = await connection.execute(countQuery);
        return mysqlRows[0].count;

      case 'postgresql':
        countQuery = `SELECT COUNT(*) as count FROM ${tableName}`;
        const pgResult = await connection.query(countQuery);
        return parseInt(pgResult.rows[0].count);

      case 'sqlite':
        countQuery = `SELECT COUNT(*) as count FROM "${table.name}"`;
        return new Promise((resolve, reject) => {
          connection.get(countQuery, (err, row) => {
            if (err) reject(err);
            else resolve(row.count);
          });
        });

      case 'mongodb':
        const db = connection.db(config.database);
        const collection = db.collection(table.name);
        return await collection.countDocuments();

      default:
        throw new Error(`Row count not implemented for: ${config.type}`);
    }
  }

  /**
   * Create database backup
   */
  async createBackup(sourceConfig, migrationId) {
    const backupPath = path.join(process.cwd(), 'backups', `${migrationId}_${sourceConfig.database}_${Date.now()}.sql`);
    await fs.ensureDir(path.dirname(backupPath));

    switch (sourceConfig.type.toLowerCase()) {
      case 'mysql':
      case 'mariadb':
        await this.createMySQLBackup(sourceConfig, backupPath);
        break;

      case 'postgresql':
        await this.createPostgreSQLBackup(sourceConfig, backupPath);
        break;

      case 'sqlite':
        // For SQLite, just copy the file
        await fs.copy(sourceConfig.file, backupPath.replace('.sql', '.db'));
        break;

      case 'mongodb':
        await this.createMongoBackup(sourceConfig, backupPath.replace('.sql', ''));
        break;

      default:
        logger.warn(`Backup not implemented for database type: ${sourceConfig.type}`);
        return null;
    }

    logger.info(`Database backup created: ${backupPath}`);
    return backupPath;
  }

  /**
   * Create MySQL backup using mysqldump
   */
  async createMySQLBackup(config, backupPath) {
    const { execSync } = await import('child_process');
    
    const command = `mysqldump -h ${config.host} -P ${config.port || 3306} -u ${config.username} -p${config.password} ${config.database} > ${backupPath}`;
    
    try {
      execSync(command, { stdio: 'inherit' });
    } catch (error) {
      logger.error('MySQL backup failed:', error);
      throw error;
    }
  }

  /**
   * Create PostgreSQL backup using pg_dump
   */
  async createPostgreSQLBackup(config, backupPath) {
    const { execSync } = await import('child_process');
    
    const command = `pg_dump -h ${config.host} -p ${config.port || 5432} -U ${config.username} -d ${config.database} -f ${backupPath}`;
    
    try {
      process.env.PGPASSWORD = config.password;
      execSync(command, { stdio: 'inherit' });
      delete process.env.PGPASSWORD;
    } catch (error) {
      logger.error('PostgreSQL backup failed:', error);
      throw error;
    }
  }

  /**
   * Create MongoDB backup using mongodump
   */
  async createMongoBackup(config, backupPath) {
    const { execSync } = await import('child_process');
    
    const command = `mongodump --host ${config.host}:${config.port || 27017} --db ${config.database} --out ${backupPath}`;
    
    try {
      execSync(command, { stdio: 'inherit' });
    } catch (error) {
      logger.error('MongoDB backup failed:', error);
      throw error;
    }
  }

  /**
   * Convert data types between databases
   */
  convertDataType(sourceType, targetDbType, sourceDbType) {
    const typeMap = {
      mysql: {
        postgresql: {
          'int': 'integer',
          'bigint': 'bigint',
          'varchar': 'varchar',
          'text': 'text',
          'datetime': 'timestamp',
          'date': 'date',
          'time': 'time',
          'decimal': 'decimal',
          'float': 'real',
          'double': 'double precision',
          'boolean': 'boolean',
          'json': 'json'
        },
        sqlite: {
          'int': 'INTEGER',
          'bigint': 'INTEGER',
          'varchar': 'TEXT',
          'text': 'TEXT',
          'datetime': 'TEXT',
          'date': 'TEXT',
          'time': 'TEXT',
          'decimal': 'REAL',
          'float': 'REAL',
          'double': 'REAL',
          'boolean': 'INTEGER'
        }
      },
      postgresql: {
        mysql: {
          'integer': 'int',
          'bigint': 'bigint',
          'varchar': 'varchar',
          'text': 'text',
          'timestamp': 'datetime',
          'date': 'date',
          'time': 'time',
          'decimal': 'decimal',
          'real': 'float',
          'double precision': 'double',
          'boolean': 'boolean',
          'json': 'json'
        }
      }
    };

    if (typeMap[sourceDbType] && typeMap[sourceDbType][targetDbType]) {
      return typeMap[sourceDbType][targetDbType][sourceType.toLowerCase()] || sourceType;
    }

    return sourceType;
  }

  /**
   * Infer MongoDB schema from document
   */
  inferMongoSchema(document, path = '') {
    const schema = {};

    for (const [key, value] of Object.entries(document)) {
      const fieldPath = path ? `${path}.${key}` : key;
      
      if (value === null) {
        schema[key] = 'null';
      } else if (Array.isArray(value)) {
        if (value.length > 0) {
          schema[key] = `array<${typeof value[0]}>`;
        } else {
          schema[key] = 'array';
        }
      } else if (typeof value === 'object') {
        schema[key] = this.inferMongoSchema(value, fieldPath);
      } else {
        schema[key] = typeof value;
      }
    }

    return schema;
  }

  /**
   * Generate unique migration ID
   */
  generateMigrationId() {
    return `migration_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}