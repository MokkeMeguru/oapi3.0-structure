import yaml
import os
import argparse
import re
from pathlib import Path
import shutil
from collections import OrderedDict

# Represent OrderedDict in YAML as a regular mapping
yaml.add_representer(OrderedDict, lambda dumper, data: dumper.represent_mapping('tag:yaml.org,2002:map', data.items()))

def unify_duplicate_schemas(spec):
    """
    Finds and unifies duplicate schemas (e.g., User and User_1) in place.
    """
    schemas = spec.get('components', {}).get('schemas', {})
    if not schemas:
        return
    dup_map = {name: re.sub(r'_\d+$', '', name) for name in schemas if re.search(r'_\d+$', name)}
    if not dup_map:
        return

    ref_map = {f"#/components/schemas/{dup}": f"#/components/schemas/{canon}" 
               for dup, canon in dup_map.items() if canon in schemas}

    def _replace_refs_recursive(obj):
        if isinstance(obj, dict):
            if '$ref' in obj and obj['$ref'] in ref_map:
                obj['$ref'] = ref_map[obj['$ref']]
            for value in obj.values():
                _replace_refs_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                _replace_refs_recursive(item)

    _replace_refs_recursive(spec)
    for dup_name in dup_map:
        if dup_name in schemas:
            del schemas[dup_name]

def find_schema_sub_dir(schema_name, openapi_spec, visited=None):
    """Finds all tags associated with a schema and returns a subdirectory name."""
    if visited is None:
        visited = set()
    if schema_name in visited:
        return None # Avoid recursion
    visited.add(schema_name)

    associated_tags = set()

    # Search in paths
    for path_item in openapi_spec.get('paths', {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict): continue
            op_str = yaml.dump(operation)
            if f"#/components/schemas/{schema_name}" in op_str:
                if 'tags' in operation and operation['tags']:
                    associated_tags.update(operation['tags'])
    
    # Search in other schemas
    for other_schema_name, other_schema_val in openapi_spec.get('components',{}).get('schemas',{}).items():
        if schema_name == other_schema_name: continue
        schema_str = yaml.dump(other_schema_val)
        if f"#/components/schemas/{schema_name}" in schema_str:
            parent_tags = find_schema_sub_dir(other_schema_name, openapi_spec, visited)
            if parent_tags:
                associated_tags.add(parent_tags)

    if len(associated_tags) > 1:
        return "shared"
    elif len(associated_tags) == 1:
        return associated_tags.pop()
    else:
        return ""

def resolve_refs(obj, current_file_path, schema_to_file_map):
    """Recursively resolve $refs within an object to relative file paths."""
    if isinstance(obj, dict):
        if '$ref' in obj:
            ref_path = obj['$ref']
            if ref_path.startswith('#/components/schemas/'):
                schema_name = ref_path.split('/')[-1]
                if schema_name in schema_to_file_map:
                    target_path = schema_to_file_map[schema_name]
                    relative_path = os.path.relpath(target_path, start=current_file_path.parent)
                    obj['$ref'] = relative_path.replace(os.path.sep, '/')
        for key, value in obj.items():
            resolve_refs(value, current_file_path, schema_to_file_map)
    elif isinstance(obj, list):
        for item in obj:
            resolve_refs(item, current_file_path, schema_to_file_map)

def decompose_openapi(input_file, output_dir):
    # スクリプトのディレクトリからプロジェクトルートに移動
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # 入力ファイルパスが相対パスの場合、プロジェクトルートからの相対パスとして解釈
    input_path = Path(input_file)
    if not input_path.is_absolute():
        input_path = project_root / input_file
        
    with open(input_path, 'r', encoding='utf-8') as f:
        openapi_spec = yaml.safe_load(f)

    unify_duplicate_schemas(openapi_spec)
    
    # 出力パスが相対パスの場合、プロジェクトルートからの相対パスとして解釈
    output_path = Path(output_dir)
    if not output_path.is_absolute():
        output_path = project_root / output_dir
        
    paths_dir = output_path / 'paths'
    components_dir = output_path / 'components' / 'schemas'

    if paths_dir.exists(): shutil.rmtree(paths_dir)
    if components_dir.exists(): shutil.rmtree(components_dir)
    if (output_path / 'root.yaml').exists(): os.remove(output_path / 'root.yaml')

    os.makedirs(paths_dir, exist_ok=True)

    all_schemas = openapi_spec.get('components', {}).get('schemas', {})

    path_local_schema_names = {s for s in all_schemas if s.endswith(('Request', 'Response', 'RequestBody', 'ResponseBody'))}
    global_schema_names = set(all_schemas.keys()) - path_local_schema_names

    global_schema_to_file_map = {}
    for schema_name in sorted(list(global_schema_names)):
        sub_dir = find_schema_sub_dir(schema_name, openapi_spec)
        schema_output_dir = components_dir / sub_dir
        os.makedirs(schema_output_dir, exist_ok=True)
        schema_file = schema_output_dir / f'{schema_name}.yaml'
        global_schema_to_file_map[schema_name] = schema_file

    for schema_name in sorted(list(global_schema_names)):
        schema_file = global_schema_to_file_map[schema_name]
        schema_obj = all_schemas[schema_name]
        resolve_refs(schema_obj, schema_file, global_schema_to_file_map)
        with open(schema_file, 'w', encoding='utf-8') as f:
            yaml.dump(schema_obj, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    new_paths = OrderedDict()
    for path, path_item in sorted(openapi_spec.get('paths', {}).items()):
        path_parts = [p for p in path.split('/') if p and '{' not in p]
        sub_dir = path_parts[0] if path_parts else ''
        file_name_base = path.replace('/', '__').replace('{', '').replace('}', '')[2:]
        file_name = f'{file_name_base}.yaml'

        path_output_dir = paths_dir / sub_dir
        os.makedirs(path_output_dir, exist_ok=True)
        path_file = path_output_dir / file_name

        local_schemas = OrderedDict()
        path_item_str = yaml.dump(path_item)
        
        # Find directly referenced schemas
        directly_referenced = set()
        for schema_name in sorted(list(path_local_schema_names)):
            if f"#/components/schemas/{schema_name}" in path_item_str:
                directly_referenced.add(schema_name)
        
        # Find recursively referenced local schemas
        def find_local_dependencies(schema_name, visited=None):
            if visited is None:
                visited = set()
            if schema_name in visited or schema_name not in all_schemas:
                return set()
            visited.add(schema_name)
            
            dependencies = set()
            schema_str = yaml.dump(all_schemas[schema_name])
            for local_schema in path_local_schema_names:
                if local_schema != schema_name and f"#/components/schemas/{local_schema}" in schema_str:
                    dependencies.add(local_schema)
                    dependencies.update(find_local_dependencies(local_schema, visited.copy()))
            return dependencies
        
        # Include all related local schemas
        included_schemas = set(directly_referenced)
        for schema_name in directly_referenced:
            included_schemas.update(find_local_dependencies(schema_name))
        
        for schema_name in sorted(included_schemas):
            local_schemas[schema_name] = all_schemas[schema_name]
        
        file_content = OrderedDict()
        file_content["operations"] = OrderedDict(sorted(path_item.items(), key=lambda i: ['get', 'post', 'put', 'delete'].index(i[0]) if i[0] in ['get', 'post', 'put', 'delete'] else 100))

        if local_schemas:
            file_content["components"] = OrderedDict([("schemas", local_schemas)])

        resolve_refs(file_content, path_file, global_schema_to_file_map)

        with open(path_file, 'w', encoding='utf-8') as f:
            yaml.dump(file_content, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        ref_prefix = f'./paths/{sub_dir}/' if sub_dir else './paths/'
        new_paths[path] = {'$ref': f'{ref_prefix}{file_name}#/operations'}

    final_root = OrderedDict()
    final_root['openapi'] = openapi_spec.get('openapi')
    final_root['info'] = openapi_spec.get('info')
    final_root['paths'] = new_paths

    with open(output_path / 'root.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(final_root, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"Decomposition complete. Files saved to {output_dir}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Decompose an OpenAPI YAML file according to README conventions.')
    parser.add_argument('input_file', help='The input OpenAPI YAML file to decompose.')
    parser.add_argument('--output', dest='output_dir', default='decomposed',
                        help='The output directory for the decomposed files.')
    args = parser.parse_args()

    decompose_openapi(args.input_file, args.output_dir)
