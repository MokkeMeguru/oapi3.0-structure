# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a sample repository demonstrating how to structure and manage OpenAPI 3.0 definitions using a modular, decomposed approach. The project shows how to split large OpenAPI specifications into manageable, reusable components while maintaining compatibility with openapi-generator-cli.

## Common Commands

- `make gen` - Bundles all YAML files into a single OpenAPI spec using openapi-generator-cli
- `make format` - Formats all YAML files using yamlfmt via Docker
- `make lint` - Lints OpenAPI specification using Redocly
- `make check-circular` - Detects circular references in schema files
- `make help` - Shows available commands
- `./test.sh` - End-to-end validation: decomposes → recomposes → compares for consistency
- `python scripts/decompose.py input.yaml --output .` - Decomposes monolithic OpenAPI file into structured format

## Architecture & Reference Patterns

The project uses three distinct `$ref` patterns that must be followed:

**Pattern 1: Root → Paths**
```yaml
# root.yaml references path operations
/users/{userId}:
  $ref: "./paths/users/users__userId.yaml#/operations"
```

**Pattern 2: Paths → Components** 
```yaml
# Path files define local schemas that reference global components
GetUserByIdResponse:
  $ref: "../../components/schemas/users/User.yaml"
```

**Pattern 3: Components → Components**
```yaml
# Schema files reference other schemas
recentPosts:
  type: array
  items:
    $ref: "./Post.yaml"
```

## File Organization

- `root.yaml` - Main entry point with API metadata and path references
- `paths/` - Individual endpoint definitions organized by domain (users/, products/)
- `components/schemas/` - Reusable data models organized by domain + shared components
- `resolved/` - Generated consolidated OpenAPI specification

## Naming Conventions

- **Path files**: `domain__resource__subresource.yaml` (e.g., `users__userId__posts.yaml`)
- **Schema files**: `ModelName.yaml` (e.g., `User.yaml`, `Post.yaml`) 
- **Local schemas in path files**: `[operationId]Request`, `[operationId]Response`, `[operationId]RequestBody`, `[operationId]ResponseBody`
- **Shared schemas**: Located in `components/schemas/shared/`

## Development Workflow

1. **Adding New Endpoints**: Create path file in `paths/domain/`, define operations with local schemas, reference global components, update `root.yaml`
2. **Testing Changes**: Run `make gen` to rebuild, use `test.sh` for validation, `make format` for consistency
3. **Schema Management**: Domain-specific in `components/schemas/domain/`, cross-domain in `shared/`

## Circular Reference Management

**Problem**: Circular references (e.g., `User.yaml` ↔ `Post.yaml`) cause openapi-generator-cli to generate duplicate schemas like `User_1`, `Post_1`.

**Detection**: Use `make check-circular` to identify circular references before generation.

**Solutions**:
- **One-way references**: Remove circular dependency (e.g., remove `recentPosts` from `User.yaml`)
- **Intermediate schemas**: Create summary schemas without circular properties (e.g., `PostSummary.yaml`)
- **allOf composition**: Use `allOf` in response schemas to add properties only where needed

## Python Utilities

- `scripts/decompose.py` - Breaks down monolithic OpenAPI files into the structured format
- `scripts/compare_yamls.py` - Validates that decomposed → recomposed YAML matches original
- `scripts/check_circular.py` - Detects circular references in schema files
- `test.sh` - End-to-end validation script using Docker for reproducible builds

This architecture works around OpenAPI 3.0 `$ref` limitations while maintaining generator compatibility and avoiding duplicate schema issues.