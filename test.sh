#!/bin/bash

set -e

TEST_DIR="test"
ORIGINAL_OPENAPI="resolved/openapi/openapi.yaml"

# Clean up previous test run
rm -rf "$TEST_DIR"

# 1. Create test directory and copy original openapi.yaml
echo "Creating test directory and copying original openapi.yaml..."
mkdir -p "$TEST_DIR"
cp "$ORIGINAL_OPENAPI" "$TEST_DIR/original_openapi.yaml"

# 2. Decompose the copied openapi.yaml
echo "Decomposing openapi.yaml..."
python3 decompose.py "$TEST_DIR/original_openapi.yaml" --output "$TEST_DIR"

# 3. Recombine the decomposed files using openapi-generator-cli
echo "Recombining decomposed files using openapi-generator-cli..."
mkdir -p "$TEST_DIR/resolved"
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd)/$TEST_DIR:/local" openapitools/openapi-generator-cli generate \
  -i /local/root.yaml \
  -g openapi-yaml \
  -o /local/resolved --skip-validate-spec

# 4. Compare the original and re-combined openapi.yaml files
echo "Comparing original and re-combined openapi.yaml files..."
python3 compare_yamls.py "$TEST_DIR/original_openapi.yaml" "$TEST_DIR/resolved/openapi/openapi.yaml"

echo "Test completed successfully!"
