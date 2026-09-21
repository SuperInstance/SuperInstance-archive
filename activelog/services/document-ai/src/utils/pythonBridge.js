const { spawn } = require('child_process');
const path = require('path');
const logger = require('./logger');

class PythonBridge {
  static async executeScript(scriptPath, args = [], options = {}) {
    return new Promise((resolve, reject) => {
      const pythonPath = options.pythonPath || 'python3';
      const timeout = options.timeout || 300000; // 5 minutes default
      
      logger.info(`Executing Python script: ${scriptPath} with args: ${JSON.stringify(args)}`);
      
      const pythonProcess = spawn(pythonPath, [scriptPath, ...args], {
        cwd: path.dirname(scriptPath),
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let stdout = '';
      let stderr = '';

      pythonProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      pythonProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      const timeoutId = setTimeout(() => {
        pythonProcess.kill('SIGTERM');
        reject(new Error(`Python script execution timeout: ${scriptPath}`));
      }, timeout);

      pythonProcess.on('close', (code) => {
        clearTimeout(timeoutId);
        
        if (code === 0) {
          try {
            const result = stdout.trim() ? JSON.parse(stdout) : {};
            logger.info(`Python script completed successfully: ${scriptPath}`);
            resolve(result);
          } catch (parseError) {
            logger.error(`Failed to parse Python script output: ${parseError.message}`);
            resolve({ raw_output: stdout, stderr });
          }
        } else {
          const error = new Error(`Python script failed with code ${code}: ${stderr}`);
          logger.error(`Python script error: ${scriptPath}`, { code, stderr, stdout });
          reject(error);
        }
      });

      pythonProcess.on('error', (error) => {
        clearTimeout(timeoutId);
        logger.error(`Failed to start Python script: ${scriptPath}`, error);
        reject(error);
      });

      // Send input data if provided
      if (options.input) {
        pythonProcess.stdin.write(JSON.stringify(options.input));
        pythonProcess.stdin.end();
      }
    });
  }

  static async processDocument(operation, filepath, options = {}) {
    const scriptMap = {
      'extract_text': path.join(__dirname, '../processors/textExtractor.py'),
      'classify': path.join(__dirname, '../ai/documentClassifier.py'),
      'extract_ner': path.join(__dirname, '../ai/nerExtractor.py'),
      'summarize': path.join(__dirname, '../ai/documentSummarizer.py'),
      'extract_tables': path.join(__dirname, '../processors/tableExtractor.py'),
      'detect_language': path.join(__dirname, '../utils/languageSupport.py'),
      'vector_search': path.join(__dirname, '../ai/vectorSearch.py')
    };

    const scriptPath = scriptMap[operation];
    if (!scriptPath) {
      throw new Error(`Unknown operation: ${operation}`);
    }

    const args = [filepath];
    if (options.output_format) {
      args.push('--output-format', options.output_format);
    }
    if (options.config) {
      args.push('--config', JSON.stringify(options.config));
    }

    return await this.executeScript(scriptPath, args, {
      timeout: options.timeout,
      input: options.input
    });
  }

  static async batchProcess(operations, filepath, options = {}) {
    const results = {};
    
    for (const operation of operations) {
      try {
        results[operation] = await this.processDocument(operation, filepath, options);
      } catch (error) {
        logger.error(`Batch processing failed for operation ${operation}:`, error);
        results[operation] = { error: error.message };
      }
    }
    
    return results;
  }

  static async healthCheck() {
    try {
      const result = await this.executeScript(
        path.join(__dirname, '../scripts/health_check.py'),
        [],
        { timeout: 30000 }
      );
      return result;
    } catch (error) {
      logger.error('Python health check failed:', error);
      return { status: 'error', message: error.message };
    }
  }
}

module.exports = PythonBridge;