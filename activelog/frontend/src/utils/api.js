/**
 * API Client for communicating with backend services
 */

import { ServiceStatusManager } from './serviceStatus.js';

class ApiClientClass {
    constructor() {
        this.baseURL = '/api';
        this.authToken = null;
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
        this.retryAttempts = 2;
        this.retryDelay = 1000;
    }

    setAuthToken(token) {
        this.authToken = token;
    }

    getHeaders(customHeaders = {}) {
        const headers = { ...this.defaultHeaders, ...customHeaders };
        
        if (this.authToken) {
            headers['Authorization'] = `Bearer ${this.authToken}`;
        }
        
        return headers;
    }

    async request(method, endpoint, data = null, customHeaders = {}) {
        // Check if we should use mock mode
        if (ServiceStatusManager.isMockMode() && this.shouldUseMockForEndpoint(endpoint)) {
            console.warn(`Using mock response for ${method} ${endpoint} - service unavailable`);
            return await ServiceStatusManager.getMockResponse(endpoint, method, data);
        }

        const url = `${this.baseURL}${endpoint}`;
        const headers = this.getHeaders(customHeaders);

        const config = {
            method: method.toUpperCase(),
            headers
        };

        if (data) {
            if (data instanceof FormData) {
                // Remove Content-Type header for FormData (browser will set it with boundary)
                delete config.headers['Content-Type'];
                config.body = data;
            } else {
                config.body = JSON.stringify(data);
            }
        }

        let lastError = null;
        
        // Retry logic with exponential backoff
        for (let attempt = 0; attempt <= this.retryAttempts; attempt++) {
            try {
                const response = await fetch(url, config);
                
                // Handle different response types
                if (!response.ok) {
                    const errorData = await this.parseResponse(response);
                    const error = new Error(errorData.detail || errorData.message || `HTTP ${response.status}`);
                    error.status = response.status;
                    error.statusText = response.statusText;
                    
                    // Don't retry client errors (4xx)
                    if (response.status >= 400 && response.status < 500) {
                        throw error;
                    }
                    
                    lastError = error;
                    if (attempt < this.retryAttempts) {
                        await this.delay(this.retryDelay * Math.pow(2, attempt));
                        continue;
                    }
                    throw error;
                }

                return await this.parseResponse(response);
            } catch (error) {
                lastError = error;
                
                // Don't retry on client errors or if it's the last attempt
                if (error.status >= 400 && error.status < 500 || attempt >= this.retryAttempts) {
                    break;
                }
                
                // Only retry on network errors or 5xx server errors
                if (attempt < this.retryAttempts) {
                    console.warn(`API ${method.toUpperCase()} ${endpoint} failed (attempt ${attempt + 1}), retrying...`);
                    await this.delay(this.retryDelay * Math.pow(2, attempt));
                }
            }
        }

        console.error(`API ${method.toUpperCase()} ${endpoint} failed after ${this.retryAttempts + 1} attempts:`, lastError);
        
        // If all retries failed and we have mock mode available, use it as fallback
        if (this.shouldUseMockForEndpoint(endpoint)) {
            console.warn(`Falling back to mock response for ${method} ${endpoint}`);
            return await ServiceStatusManager.getMockResponse(endpoint, method, data);
        }
        
        throw lastError;
    }

    shouldUseMockForEndpoint(endpoint) {
        // Don't use mock for critical auth endpoints unless in mock mode
        const authEndpoints = ['/auth/login', '/auth/register', '/auth/logout'];
        if (authEndpoints.some(e => endpoint.includes(e))) {
            return false;
        }
        
        // Use mock for other endpoints if services are unavailable
        return true;
    }

    async delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async parseResponse(response) {
        const contentType = response.headers.get('content-type');
        
        if (contentType?.includes('application/json')) {
            return await response.json();
        } else if (contentType?.includes('text/')) {
            return await response.text();
        } else {
            return await response.blob();
        }
    }

    // HTTP Methods
    async get(endpoint, headers = {}) {
        return this.request('GET', endpoint, null, headers);
    }

    async post(endpoint, data = null, headers = {}) {
        return this.request('POST', endpoint, data, headers);
    }

    async put(endpoint, data = null, headers = {}) {
        return this.request('PUT', endpoint, data, headers);
    }

    async patch(endpoint, data = null, headers = {}) {
        return this.request('PATCH', endpoint, data, headers);
    }

    async delete(endpoint, headers = {}) {
        return this.request('DELETE', endpoint, null, headers);
    }

    // File upload with progress
    async uploadFile(endpoint, file, onProgress = null, additionalData = {}) {
        const formData = new FormData();
        formData.append('file', file);
        
        // Add additional form data
        Object.entries(additionalData).forEach(([key, value]) => {
            formData.append(key, value);
        });

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            if (onProgress) {
                xhr.upload.addEventListener('progress', (event) => {
                    if (event.lengthComputable) {
                        const percentComplete = (event.loaded / event.total) * 100;
                        onProgress(percentComplete, event.loaded, event.total);
                    }
                });
            }

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (error) {
                        resolve(xhr.responseText);
                    }
                } else {
                    reject(new Error(`Upload failed: ${xhr.statusText}`));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed'));
            });

            xhr.open('POST', `${this.baseURL}${endpoint}`);
            
            // Set auth header if available
            if (this.authToken) {
                xhr.setRequestHeader('Authorization', `Bearer ${this.authToken}`);
            }
            
            xhr.send(formData);
        });
    }

    // Batch upload multiple files
    async uploadFiles(endpoint, files, onProgress = null, additionalData = {}) {
        const results = [];
        const totalFiles = files.length;
        let completedFiles = 0;

        for (const file of files) {
            try {
                const result = await this.uploadFile(endpoint, file, (progress) => {
                    if (onProgress) {
                        const overallProgress = ((completedFiles + (progress / 100)) / totalFiles) * 100;
                        onProgress(overallProgress, file.name, progress);
                    }
                }, additionalData);
                
                results.push({ file: file.name, success: true, result });
                completedFiles++;
            } catch (error) {
                results.push({ file: file.name, success: false, error: error.message });
                completedFiles++;
            }
        }

        return results;
    }
}

export const ApiClient = new ApiClientClass();