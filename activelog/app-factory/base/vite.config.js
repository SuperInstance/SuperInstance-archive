import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig(({ mode }) => {
  const appConfig = process.env.APP_CONFIG ? JSON.parse(process.env.APP_CONFIG) : {};
  
  return {
    root: '.',
    publicDir: 'public',
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: mode === 'development',
      rollupOptions: {
        input: {
          main: resolve(__dirname, 'index.html')
        }
      }
    },
    define: {
      __APP_CONFIG__: JSON.stringify(appConfig),
      __APP_NAME__: JSON.stringify(appConfig.name || 'ActiveLog'),
      __APP_VERSION__: JSON.stringify(appConfig.version || '1.0.0')
    },
    server: {
      port: appConfig.devPort || 3000,
      host: true,
      cors: true
    },
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
        '@shared': resolve(__dirname, '../shared'),
        '@themes': resolve(__dirname, '../themes'),
        '@auth': resolve(__dirname, '../auth'),
        '@sync': resolve(__dirname, '../data-sync'),
        '@ai': resolve(__dirname, '../ai-models'),
        '@settings': resolve(__dirname, '../settings')
      }
    }
  };
});