.PHONY: gen
gen:
	docker run --rm -v "$(CURDIR):/local" openapitools/openapi-generator-cli generate \
	-i /local/root.yaml \
	-g openapi-yaml \
	-o /local/resolved