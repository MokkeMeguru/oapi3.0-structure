.PHONY: gen format help

gen:
	@echo "Generating OpenAPI specification..."
	@docker run --rm -v "$(CURDIR):/local" openapitools/openapi-generator-cli generate \
	-i /local/root.yaml \
	-g openapi-yaml \
	-o /local/resolved
	@echo "Done."

format:
	@echo "Formatting YAML files using yamlfmt..."
	@find . -path ./resolved -prune -o -path ./.git -prune -o -name "*.yaml" -print0 | xargs -0 -I {} docker run --rm -v "$(CURDIR):/project" ghcr.io/google/yamlfmt:latest {} --in-place
	@echo "Done."

help:
	@echo "Available commands:"
	@echo "  gen     - Generate openapi.yaml from root.yaml"
	@echo "  format  - Format all YAML files in the project using yamlfmt"
	@echo "  help    - Show this help message"