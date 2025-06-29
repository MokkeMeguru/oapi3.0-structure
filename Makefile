.PHONY: gen format lint check-circular help

gen:
	@echo "Generating OpenAPI specification..."
	@docker run --rm --user "$(id -u):$(id -g)" -v "$(CURDIR):/local" openapitools/openapi-generator-cli generate \
	-i /local/root.yaml \
	-g openapi-yaml \
	-o /local/resolved
	@echo "Done."

format:
	@echo "Formatting YAML files using yamlfmt..."
	@find . -path ./resolved -prune -o -path ./.git -prune -o -name "*.yaml" -print0 | xargs -0 -I {} docker run --rm -v "$(CURDIR):/project" ghcr.io/google/yamlfmt:latest {} --in-place
	@echo "Done."

lint:
	@echo "Linting OpenAPI specification..."
	@docker run --rm -v "$(CURDIR):/spec" redocly/cli@1.34.4 lint root.yaml
	@echo "Done."

check-circular:
	@python3 scripts/check_circular.py

help:
	@echo "Available commands:"
	@echo "  gen           - Generate openapi.yaml from root.yaml"
	@echo "  format        - Format all YAML files in the project using yamlfmt"
	@echo "  lint          - Lint OpenAPI specification using Redocly"
	@echo "  check-circular - Check for circular references in schema files"
	@echo "  help          - Show this help message"