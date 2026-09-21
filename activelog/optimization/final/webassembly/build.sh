#!/bin/bash

# WebAssembly Build Script for ActiveLog Optimization
# Requires Emscripten SDK to be installed and activated

set -e

echo "🔨 Building WebAssembly modules for ActiveLog optimization..."

# Check if Emscripten is available
if ! command -v emcc &> /dev/null; then
    echo "❌ Emscripten not found. Please install and activate the Emscripten SDK:"
    echo "   git clone https://github.com/emscripten-core/emsdk.git"
    echo "   cd emsdk"
    echo "   ./emsdk install latest"
    echo "   ./emsdk activate latest"
    echo "   source ./emsdk_env.sh"
    exit 1
fi

# Create output directory
mkdir -p ../build/wasm

echo "📦 Building image processor module..."

# Build image processor with optimizations
emcc image-processor.c \
    -o ../build/wasm/image-processor.js \
    -s WASM=1 \
    -s EXPORT_ES6=1 \
    -s MODULARIZE=1 \
    -s USE_ES6_IMPORT_META=0 \
    -s EXPORT_NAME="ImageProcessor" \
    -s EXPORTED_FUNCTIONS='["_resize_image", "_gaussian_blur", "_sharpen_image", "_adjust_brightness_contrast", "_adjust_color_temperature", "_edge_detection", "_adjust_hsv", "_allocate_memory", "_free_memory", "_malloc", "_free"]' \
    -s EXPORTED_RUNTIME_METHODS='["ccall", "cwrap"]' \
    -s ALLOW_MEMORY_GROWTH=1 \
    -s INITIAL_MEMORY=16777216 \
    -s MAXIMUM_MEMORY=134217728 \
    -s STACK_SIZE=1048576 \
    -s NO_EXIT_RUNTIME=1 \
    -s ENVIRONMENT='web,worker' \
    -s FILESYSTEM=0 \
    -O3 \
    -s ASSERTIONS=0 \
    -s MALLOC=emmalloc \
    --bind \
    --closure 1

echo "📦 Building data processing module..."

# Build data processing module
emcc data-processor.c \
    -o ../build/wasm/data-processor.js \
    -s WASM=1 \
    -s EXPORT_ES6=1 \
    -s MODULARIZE=1 \
    -s USE_ES6_IMPORT_META=0 \
    -s EXPORT_NAME="DataProcessor" \
    -s EXPORTED_FUNCTIONS='["_sort_array", "_search_binary", "_hash_string", "_compress_data", "_decompress_data", "_calculate_hash", "_encrypt_data", "_decrypt_data", "_allocate_memory", "_free_memory", "_malloc", "_free"]' \
    -s EXPORTED_RUNTIME_METHODS='["ccall", "cwrap"]' \
    -s ALLOW_MEMORY_GROWTH=1 \
    -s INITIAL_MEMORY=8388608 \
    -s MAXIMUM_MEMORY=67108864 \
    -s NO_EXIT_RUNTIME=1 \
    -s ENVIRONMENT='web,worker' \
    -s FILESYSTEM=0 \
    -O3 \
    -s ASSERTIONS=0 \
    -s MALLOC=emmalloc \
    --bind \
    --closure 1

echo "📦 Building crypto module..."

# Build crypto module for secure operations
emcc crypto-processor.c \
    -o ../build/wasm/crypto-processor.js \
    -s WASM=1 \
    -s EXPORT_ES6=1 \
    -s MODULARIZE=1 \
    -s USE_ES6_IMPORT_META=0 \
    -s EXPORT_NAME="CryptoProcessor" \
    -s EXPORTED_FUNCTIONS='["_sha256_hash", "_aes_encrypt", "_aes_decrypt", "_generate_random", "_pbkdf2_derive", "_allocate_memory", "_free_memory", "_malloc", "_free"]' \
    -s EXPORTED_RUNTIME_METHODS='["ccall", "cwrap"]' \
    -s ALLOW_MEMORY_GROWTH=1 \
    -s INITIAL_MEMORY=4194304 \
    -s MAXIMUM_MEMORY=33554432 \
    -s NO_EXIT_RUNTIME=1 \
    -s ENVIRONMENT='web,worker' \
    -s FILESYSTEM=0 \
    -O3 \
    -s ASSERTIONS=0 \
    -s MALLOC=emmalloc \
    --bind \
    --closure 1

echo "📦 Building math processor module..."

# Build math processor for heavy calculations
emcc math-processor.c \
    -o ../build/wasm/math-processor.js \
    -s WASM=1 \
    -s EXPORT_ES6=1 \
    -s MODULARIZE=1 \
    -s USE_ES6_IMPORT_META=0 \
    -s EXPORT_NAME="MathProcessor" \
    -s EXPORTED_FUNCTIONS='["_matrix_multiply", "_fft_transform", "_statistical_analysis", "_numerical_integration", "_polynomial_regression", "_distance_calculations", "_allocate_memory", "_free_memory", "_malloc", "_free"]' \
    -s EXPORTED_RUNTIME_METHODS='["ccall", "cwrap"]' \
    -s ALLOW_MEMORY_GROWTH=1 \
    -s INITIAL_MEMORY=8388608 \
    -s MAXIMUM_MEMORY=67108864 \
    -s NO_EXIT_RUNTIME=1 \
    -s ENVIRONMENT='web,worker' \
    -s FILESYSTEM=0 \
    -O3 \
    -s ASSERTIONS=0 \
    -s MALLOC=emmalloc \
    --bind \
    --closure 1

# Create TypeScript declarations
echo "📝 Generating TypeScript declarations..."

cat > ../build/wasm/image-processor.d.ts << 'EOF'
export interface ImageProcessorModule {
  ready: Promise<void>;
  
  resize_image(
    src_data: number, src_width: number, src_height: number,
    dst_data: number, dst_width: number, dst_height: number
  ): void;
  
  gaussian_blur(data: number, width: number, height: number, radius: number): void;
  sharpen_image(data: number, width: number, height: number, amount: number): void;
  adjust_brightness_contrast(data: number, width: number, height: number, brightness: number, contrast: number): void;
  adjust_color_temperature(data: number, width: number, height: number, temperature: number): void;
  edge_detection(src_data: number, dst_data: number, width: number, height: number, threshold: number): void;
  adjust_hsv(data: number, width: number, height: number, hue_shift: number, saturation_mult: number, value_mult: number): void;
  
  allocate_memory(size: number): number;
  free_memory(ptr: number): void;
  
  HEAPU8: Uint8Array;
  _malloc(size: number): number;
  _free(ptr: number): void;
}

declare const ImageProcessor: () => Promise<ImageProcessorModule>;
export default ImageProcessor;
EOF

cat > ../build/wasm/data-processor.d.ts << 'EOF'
export interface DataProcessorModule {
  ready: Promise<void>;
  
  sort_array(data: number, length: number, element_size: number): void;
  search_binary(data: number, length: number, target: number): number;
  hash_string(str: number, length: number): number;
  compress_data(input: number, input_length: number, output: number): number;
  decompress_data(input: number, input_length: number, output: number): number;
  
  allocate_memory(size: number): number;
  free_memory(ptr: number): void;
  
  HEAPU8: Uint8Array;
  HEAP32: Int32Array;
  _malloc(size: number): number;
  _free(ptr: number): void;
}

declare const DataProcessor: () => Promise<DataProcessorModule>;
export default DataProcessor;
EOF

cat > ../build/wasm/crypto-processor.d.ts << 'EOF'
export interface CryptoProcessorModule {
  ready: Promise<void>;
  
  sha256_hash(data: number, length: number, output: number): void;
  aes_encrypt(data: number, length: number, key: number, output: number): number;
  aes_decrypt(data: number, length: number, key: number, output: number): number;
  generate_random(output: number, length: number): void;
  pbkdf2_derive(password: number, password_len: number, salt: number, salt_len: number, iterations: number, output: number, output_len: number): void;
  
  allocate_memory(size: number): number;
  free_memory(ptr: number): void;
  
  HEAPU8: Uint8Array;
  _malloc(size: number): number;
  _free(ptr: number): void;
}

declare const CryptoProcessor: () => Promise<CryptoProcessorModule>;
export default CryptoProcessor;
EOF

cat > ../build/wasm/math-processor.d.ts << 'EOF'
export interface MathProcessorModule {
  ready: Promise<void>;
  
  matrix_multiply(a: number, b: number, result: number, rows_a: number, cols_a: number, cols_b: number): void;
  fft_transform(real: number, imag: number, n: number): void;
  statistical_analysis(data: number, length: number, results: number): void;
  numerical_integration(func_ptr: number, start: number, end: number, steps: number): number;
  polynomial_regression(x: number, y: number, length: number, degree: number, coefficients: number): void;
  distance_calculations(points: number, length: number, distances: number): void;
  
  allocate_memory(size: number): number;
  free_memory(ptr: number): void;
  
  HEAPU8: Uint8Array;
  HEAPF32: Float32Array;
  HEAPF64: Float64Array;
  _malloc(size: number): number;
  _free(ptr: number): void;
}

declare const MathProcessor: () => Promise<MathProcessorModule>;
export default MathProcessor;
EOF

# Create webpack configuration for WASM modules
echo "⚙️ Creating webpack configuration..."

cat > ../build/wasm/webpack.wasm.config.js << 'EOF'
const path = require('path');

module.exports = {
  entry: {
    'wasm-loader': './wasm-loader.js'
  },
  output: {
    path: path.resolve(__dirname, '../dist'),
    filename: '[name].bundle.js',
    library: 'WASMLoader',
    libraryTarget: 'umd'
  },
  module: {
    rules: [
      {
        test: /\.wasm$/,
        type: 'asset/resource',
        generator: {
          filename: 'wasm/[name][ext]'
        }
      }
    ]
  },
  resolve: {
    extensions: ['.js', '.wasm']
  },
  experiments: {
    asyncWebAssembly: true,
    syncWebAssembly: true
  },
  optimization: {
    minimize: true
  }
};
EOF

# Check file sizes and provide optimization report
echo "📊 Build complete! File size report:"
echo "=================================="

for file in ../build/wasm/*.wasm; do
    if [ -f "$file" ]; then
        size=$(wc -c < "$file")
        size_kb=$((size / 1024))
        echo "$(basename "$file"): ${size_kb}KB"
    fi
done

echo ""
echo "✅ WebAssembly modules built successfully!"
echo "📁 Output directory: $(pwd)/../build/wasm/"
echo ""
echo "Next steps:"
echo "1. Include the generated .js files in your web application"
echo "2. Use the TypeScript declarations for type safety"
echo "3. Initialize modules asynchronously in your application"
echo ""
echo "Example usage:"
echo "  import ImageProcessor from './build/wasm/image-processor.js';"
echo "  const processor = await ImageProcessor();"
echo "  // Use processor methods..."
echo ""

echo "🎉 Build process completed successfully!"