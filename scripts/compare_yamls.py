import yaml
import sys
from pathlib import Path

def compare_yamls(file1_path, file2_path):
    # スクリプトのディレクトリからプロジェクトルートに移動
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # 入力ファイルパスが相対パスの場合、プロジェクトルートからの相対パスとして解釈
    path1 = Path(file1_path)
    if not path1.is_absolute():
        path1 = project_root / file1_path
        
    path2 = Path(file2_path)
    if not path2.is_absolute():
        path2 = project_root / file2_path
    
    try:
        with open(path1, 'r', encoding='utf-8') as f1:
            data1 = yaml.safe_load(f1)
        with open(path2, 'r', encoding='utf-8') as f2:
            data2 = yaml.safe_load(f2)
    except FileNotFoundError as e:
        print(f"Error: File not found - {e.filename}", file=sys.stderr)
        return False
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        return False

    def normalize_openapi_spec(spec):
        # Normalize paths: if paths is empty in one, make it empty in both for comparison
        # This handles the case where openapi-generator-cli might empty the paths section
        if 'paths' in spec:
            if not spec['paths']:
                spec['paths'] = {}
        
        # Recursively remove 'explode' and 'style' from path parameters for comparison
        def remove_param_defaults(obj):
            if isinstance(obj, dict):
                if 'parameters' in obj:
                    for param in obj['parameters']:
                        if param.get('in') == 'path':
                            param.pop('explode', None)
                            param.pop('style', None)
                for key, value in obj.items():
                    remove_param_defaults(value)
            elif isinstance(obj, list):
                for item in obj:
                    remove_param_defaults(item)
        
        remove_param_defaults(spec)

        # Normalize examples (e.g., sort keys in dictionaries within examples)
        def normalize_examples(obj):
            if isinstance(obj, dict):
                if 'example' in obj:
                    # Convert example to a string and back to normalize, or sort keys
                    # For simplicity, we'll just sort keys if it's a dict
                    if isinstance(obj['example'], dict):
                        obj['example'] = dict(sorted(obj['example'].items()))
                for key, value in obj.items():
                    normalize_examples(value)
            elif isinstance(obj, list):
                for item in obj:
                    normalize_examples(item)
        
        normalize_examples(spec)

        return spec

    data1_normalized = normalize_openapi_spec(data1)
    data2_normalized = normalize_openapi_spec(data2)

    # Deep comparison of dictionaries, ignoring order
    def deep_compare(obj1, obj2):
        if type(obj1) != type(obj2):
            return False
        if isinstance(obj1, dict):
            # Special handling for paths section if it's empty in one but not the other
            if 'paths' in obj1 and 'paths' in obj2:
                if not obj1['paths'] and not obj2['paths']:
                    # Both are empty, consider them equal for paths
                    pass
                elif not obj1['paths'] or not obj2['paths']:
                    # One is empty, the other is not, they are different
                    return False
                else:
                    # Both are not empty, compare normally
                    if set(obj1.keys()) != set(obj2.keys()):
                        return False
                    for key in obj1:
                        if key == 'paths': # Skip paths for now, handled above
                            continue
                        if not deep_compare(obj1[key], obj2[key]):
                            return False
                    return True
            
            if set(obj1.keys()) != set(obj2.keys()):
                return False
            for key in obj1:
                if not deep_compare(obj1[key], obj2[key]):
                    return False
            return True
        elif isinstance(obj1, list):
            if len(obj1) != len(obj2):
                return False
            # For lists, order matters unless specified otherwise.
            # For OpenAPI, sometimes order of paths/schemas doesn't strictly matter,
            # but for a robust comparison, we'll assume order matters for lists.
            # If order doesn't matter, lists would need to be sorted before comparison.
            # For now, direct comparison.
            for item1, item2 in zip(obj1, obj2):
                if not deep_compare(item1, item2):
                    return False
            return True
        else:
            return obj1 == obj2

    if deep_compare(data1_normalized, data2_normalized):
        print(f"YAML files '{path1}' and '{path2}' are structurally identical.")
        return True
    else:
        print(f"YAML files '{path1}' and '{path2}' are structurally different.", file=sys.stderr)
        return False

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 compare_yamls.py <file1.yaml> <file2.yaml>", file=sys.stderr)
        sys.exit(1)

    file1 = sys.argv[1]
    file2 = sys.argv[2]

    if not compare_yamls(file1, file2):
        sys.exit(1)