/**
 * Optimized Webpack Configuration for Bundle Size Reduction
 * Advanced configuration with multiple optimization strategies
 */

const path = require('path');
const webpack = require('webpack');
const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
const CompressionPlugin = require('compression-webpack-plugin');
const TerserPlugin = require('terser-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

const isDevelopment = process.env.NODE_ENV === 'development';
const isProduction = process.env.NODE_ENV === 'production';
const shouldAnalyze = process.env.ANALYZE === 'true';

module.exports = {
  mode: isProduction ? 'production' : 'development',
  devtool: isProduction ? 'source-map' : 'eval-cheap-module-source-map',

  entry: {
    // Main application entry
    main: './src/index.ts',
    
    // Vendor libraries (will be further split by splitChunks)
    vendor: [
      'react',
      'react-dom',
      'redux',
      'react-redux'
    ]
  },

  output: {
    path: path.resolve(__dirname, '../build'),
    filename: isProduction 
      ? 'js/[name].[contenthash:8].js'
      : 'js/[name].js',
    chunkFilename: isProduction 
      ? 'js/[name].[contenthash:8].chunk.js'
      : 'js/[name].chunk.js',
    publicPath: '/',
    clean: true,
    
    // Optimize module concatenation
    pathinfo: false,
    
    // Enable better tree shaking
    environment: {
      arrowFunction: true,
      bigIntLiteral: false,
      const: true,
      destructuring: true,
      dynamicImport: true,
      forOf: true,
      module: true,
    }
  },

  resolve: {
    extensions: ['.ts', '.tsx', '.js', '.jsx'],
    
    // Module resolution optimizations
    modules: [
      path.resolve(__dirname, '../src'),
      'node_modules'
    ],
    
    // Alias for common paths and lighter alternatives
    alias: {
      '@': path.resolve(__dirname, '../src'),
      '@components': path.resolve(__dirname, '../src/components'),
      '@utils': path.resolve(__dirname, '../src/utils'),
      '@services': path.resolve(__dirname, '../src/services'),
      '@types': path.resolve(__dirname, '../src/types'),
      
      // Lighter alternatives
      'lodash': 'lodash-es',
      'moment': 'dayjs',
      
      // React production builds
      ...(isProduction && {
        'react': 'react/cjs/react.production.min.js',
        'react-dom': 'react-dom/cjs/react-dom.production.min.js'
      })
    },
    
    // Prioritize ES modules for better tree shaking
    mainFields: ['browser', 'jsnext:main', 'main'],
    
    // Fallback for Node.js modules
    fallback: {
      'crypto': false,
      'stream': false,
      'assert': false,
      'http': false,
      'https': false,
      'os': false,
      'url': false,
      'zlib': false
    }
  },

  module: {
    // Skip parsing of known libraries without dependencies
    noParse: /^(vue|lodash|jquery)$/,
    
    rules: [
      // TypeScript/JavaScript
      {
        test: /\.(ts|tsx|js|jsx)$/,
        exclude: /node_modules/,
        use: [
          {
            loader: 'babel-loader',
            options: {
              presets: [
                [
                  '@babel/preset-env',
                  {
                    useBuiltIns: 'usage',
                    corejs: 3,
                    modules: false, // Let webpack handle modules
                    targets: {
                      browsers: ['> 1%', 'last 2 versions', 'not dead']
                    }
                  }
                ],
                ['@babel/preset-react', { runtime: 'automatic' }],
                '@babel/preset-typescript'
              ],
              plugins: [
                // Dynamic imports
                '@babel/plugin-syntax-dynamic-import',
                
                // Optimize bundle size
                ['babel-plugin-transform-imports', {
                  'lodash': {
                    'transform': 'lodash/${member}',
                    'preventFullImport': true
                  },
                  'material-ui': {
                    'transform': '@material-ui/core/esm/${member}',
                    'preventFullImport': true
                  },
                  'antd': {
                    'transform': 'antd/es/${member}',
                    'preventFullImport': true,
                    'style': true
                  }
                }],
                
                // Remove dead code
                isProduction && 'babel-plugin-dev-expression',
                isProduction && [
                  'babel-plugin-transform-react-remove-prop-types',
                  { removeImport: true }
                ]
              ].filter(Boolean),
              
              cacheDirectory: true,
              cacheCompression: false,
            }
          }
        ]
      },

      // CSS/SCSS
      {
        test: /\.s?css$/,
        use: [
          isProduction ? MiniCssExtractPlugin.loader : 'style-loader',
          {
            loader: 'css-loader',
            options: {
              modules: {
                auto: true,
                localIdentName: isProduction 
                  ? '[hash:base64:5]'
                  : '[local]--[hash:base64:5]'
              },
              sourceMap: !isProduction
            }
          },
          {
            loader: 'postcss-loader',
            options: {
              postcssOptions: {
                plugins: [
                  'autoprefixer',
                  isProduction && 'cssnano'
                ].filter(Boolean)
              }
            }
          },
          'sass-loader'
        ]
      },

      // Images
      {
        test: /\.(png|jpe?g|gif|svg|webp)$/i,
        type: 'asset',
        parser: {
          dataUrlCondition: {
            maxSize: 8192 // Inline files smaller than 8kb
          }
        },
        generator: {
          filename: 'images/[name].[hash:8][ext]'
        },
        use: isProduction ? [
          {
            loader: 'image-webpack-loader',
            options: {
              mozjpeg: { progressive: true, quality: 85 },
              optipng: { enabled: true },
              pngquant: { quality: [0.65, 0.90], speed: 4 },
              gifsicle: { interlaced: false },
              webp: { quality: 85 },
              svgo: {
                plugins: [
                  { name: 'removeViewBox', active: false },
                  { name: 'removeEmptyAttrs', active: true }
                ]
              }
            }
          }
        ] : []
      },

      // Fonts
      {
        test: /\.(woff|woff2|eot|ttf|otf)$/i,
        type: 'asset/resource',
        generator: {
          filename: 'fonts/[name].[hash:8][ext]'
        }
      }
    ]
  },

  optimization: {
    minimize: isProduction,
    
    minimizer: [
      // JavaScript minification
      new TerserPlugin({
        terserOptions: {
          parse: {
            ecma: 8,
          },
          compress: {
            ecma: 5,
            warnings: false,
            comparisons: false,
            inline: 2,
            drop_console: isProduction,
            drop_debugger: isProduction,
            pure_funcs: isProduction ? ['console.log', 'console.info'] : []
          },
          mangle: {
            safari10: true,
          },
          output: {
            ecma: 5,
            comments: false,
            ascii_only: true,
          },
        },
        parallel: true,
      }),

      // CSS minification
      new CssMinimizerPlugin({
        minimizerOptions: {
          preset: [
            'default',
            {
              discardComments: { removeAll: true },
              normalizeWhitespace: true,
              colormin: true,
              convertValues: true,
              discardDuplicates: true,
              discardEmpty: true,
              mergeRules: true,
              minifyFontValues: true,
              minifyGradients: true,
              minifyParams: true,
              minifySelectors: true,
              reduceIdents: true,
              svgo: true
            }
          ]
        }
      })
    ],

    // Advanced chunk splitting strategy
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        // Framework libraries (React, etc.)
        framework: {
          test: /[\\/]node_modules[\\/](react|react-dom|redux|react-redux)[\\/]/,
          name: 'framework',
          chunks: 'all',
          priority: 40,
          enforce: true,
          reuseExistingChunk: true
        },

        // UI libraries
        ui: {
          test: /[\\/]node_modules[\\/](@material-ui|antd|semantic-ui|bootstrap)[\\/]/,
          name: 'ui',
          chunks: 'all',
          priority: 30,
          reuseExistingChunk: true
        },

        // Utility libraries
        utils: {
          test: /[\\/]node_modules[\\/](lodash|moment|dayjs|date-fns|ramda)[\\/]/,
          name: 'utils',
          chunks: 'all',
          priority: 25,
          reuseExistingChunk: true
        },

        // Other vendor libraries
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendor',
          chunks: 'all',
          priority: 20,
          minChunks: 2,
          reuseExistingChunk: true
        },

        // Common modules across the app
        common: {
          name: 'common',
          chunks: 'all',
          minChunks: 2,
          priority: 10,
          reuseExistingChunk: true,
          enforce: true
        },

        // Default
        default: {
          minChunks: 2,
          priority: 5,
          reuseExistingChunk: true
        }
      },

      // Prevent creating chunks smaller than 20kb
      minSize: 20000,
      maxSize: 250000, // Split chunks larger than 250kb

      // Limit the number of parallel requests
      maxAsyncRequests: 30,
      maxInitialRequests: 30
    },

    // Better module concatenation
    concatenateModules: isProduction,

    // Deterministic chunk ids for better caching
    moduleIds: isProduction ? 'deterministic' : 'named',
    chunkIds: isProduction ? 'deterministic' : 'named',

    // Runtime chunk
    runtimeChunk: {
      name: 'runtime'
    },

    // Remove empty chunks
    removeEmptyChunks: true,

    // Flag dependency usage for better tree shaking
    usedExports: true,
    providedExports: true,
    sideEffects: false
  },

  plugins: [
    // Clean build directory
    new CleanWebpackPlugin(),

    // HTML generation
    new HtmlWebpackPlugin({
      template: './public/index.html',
      minify: isProduction ? {
        removeComments: true,
        collapseWhitespace: true,
        removeRedundantAttributes: true,
        useShortDoctype: true,
        removeEmptyAttributes: true,
        removeStyleLinkTypeAttributes: true,
        keepClosingSlash: true,
        minifyJS: true,
        minifyCSS: true,
        minifyURLs: true,
      } : false,
      inject: true
    }),

    // Extract CSS
    isProduction && new MiniCssExtractPlugin({
      filename: 'css/[name].[contenthash:8].css',
      chunkFilename: 'css/[name].[contenthash:8].chunk.css',
      ignoreOrder: true
    }),

    // Compression
    isProduction && new CompressionPlugin({
      filename: '[path][base].gz',
      algorithm: 'gzip',
      test: /\.(js|css|html|svg)$/,
      threshold: 8192,
      minRatio: 0.8,
      compressionOptions: {
        level: 9,
        windowBits: 15,
        memLevel: 8
      }
    }),

    // Brotli compression
    isProduction && new CompressionPlugin({
      filename: '[path][base].br',
      algorithm: 'brotliCompress',
      test: /\.(js|css|html|svg)$/,
      threshold: 8192,
      minRatio: 0.8,
      compressionOptions: {
        level: 11
      }
    }),

    // Bundle analysis
    shouldAnalyze && new BundleAnalyzerPlugin({
      analyzerMode: 'static',
      openAnalyzer: false,
      reportFilename: '../reports/bundle-analysis.html',
      defaultSizes: 'gzip',
      generateStatsFile: true,
      statsFilename: '../reports/bundle-stats.json'
    }),

    // Environment variables
    new webpack.DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV),
      'process.env.PUBLIC_URL': JSON.stringify(''),
      '__DEV__': isDevelopment
    }),

    // Module Federation (if needed)
    // new webpack.container.ModuleFederationPlugin({
    //   name: 'shell',
    //   remotes: {
    //     microfrontend1: 'microfrontend1@http://localhost:3001/remoteEntry.js'
    //   }
    // }),

    // Prefetch/Preload important chunks
    new webpack.PrefetchPlugin('./src/components/AsyncComponent'),
    
    // Ignore moment locales (saves ~200kb)
    new webpack.IgnorePlugin({
      resourceRegExp: /^\.\/locale$/,
      contextRegExp: /moment$/
    }),

    // Progress reporting
    !isDevelopment && new webpack.ProgressPlugin({
      activeModules: false,
      entries: true,
      handler(percentage, message, ...args) {
        console.info(`${Math.round(percentage * 100)}%`, message, ...args);
      }
    })
  ].filter(Boolean),

  // Development server
  ...(isDevelopment && {
    devServer: {
      hot: true,
      historyApiFallback: true,
      compress: true,
      port: 3000,
      client: {
        overlay: {
          errors: true,
          warnings: false
        }
      }
    }
  }),

  // Performance hints
  performance: {
    hints: isProduction ? 'warning' : false,
    maxEntrypointSize: 250000, // 250kb
    maxAssetSize: 250000, // 250kb
    assetFilter: (assetFilename) => {
      return !assetFilename.endsWith('.map') && 
             !assetFilename.endsWith('.gz') && 
             !assetFilename.endsWith('.br');
    }
  },

  // Stats configuration for cleaner output
  stats: {
    colors: true,
    chunks: false,
    chunkModules: false,
    modules: false,
    children: false,
    entrypoints: false,
    excludeAssets: /\.(map|gz|br)$/
  },

  // Cache configuration for faster rebuilds
  cache: {
    type: 'filesystem',
    cacheDirectory: path.resolve(__dirname, '../node_modules/.cache/webpack'),
    buildDependencies: {
      config: [__filename]
    }
  },

  // Experiments
  experiments: {
    topLevelAwait: true,
    outputModule: false
  },

  // Resolve loader
  resolveLoader: {
    modules: ['node_modules']
  }
};

// Export additional helper functions
module.exports.helpers = {
  // Bundle size budget check
  checkBudgets: (stats) => {
    const budgets = {
      'main': 250 * 1024,      // 250KB
      'vendor': 500 * 1024,    // 500KB
      'framework': 150 * 1024,  // 150KB
      'ui': 200 * 1024         // 200KB
    };

    const assets = stats.compilation.assets;
    const warnings = [];

    Object.entries(budgets).forEach(([chunk, budget]) => {
      const chunkAssets = Object.keys(assets).filter(name => 
        name.includes(chunk) && name.endsWith('.js')
      );

      chunkAssets.forEach(asset => {
        const size = assets[asset].size();
        if (size > budget) {
          warnings.push(`Bundle size warning: ${asset} (${(size / 1024).toFixed(1)}KB) exceeds budget (${(budget / 1024).toFixed(1)}KB)`);
        }
      });
    });

    return warnings;
  },

  // Generate bundle report
  generateReport: (stats) => {
    const compilation = stats.compilation;
    const chunks = Array.from(compilation.chunks);
    
    return {
      totalSize: compilation.assets ? Object.values(compilation.assets).reduce((sum, asset) => sum + asset.size(), 0) : 0,
      chunks: chunks.map(chunk => ({
        name: chunk.name,
        size: chunk.size,
        modules: Array.from(chunk.modulesIterable).length
      })),
      timestamp: new Date().toISOString()
    };
  }
};