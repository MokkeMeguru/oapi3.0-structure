#!/usr/bin/env python3
"""
循環参照検出スクリプト
OpenAPIスキーマファイル間の循環参照を検出します。
"""

import yaml
import sys
from pathlib import Path
from typing import Dict, Set, List, Optional


def load_yaml_file(file_path: Path) -> Optional[dict]:
    """YAMLファイルを読み込む"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Warning: Could not load {file_path}: {e}")
        return None


def extract_refs(content: dict, base_path: Path, project_root: Path) -> List[Path]:
    """コンテンツから$refを抽出し、正規化されたパスに変換"""
    refs = []
    
    def find_refs(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == '$ref' and isinstance(value, str):
                    # 相対パスを絶対パスに変換
                    if value.startswith('./'):
                        ref_path = (base_path.parent / value[2:]).resolve()
                        if ref_path.exists():
                            # プロジェクトルートからの相対パスに正規化
                            try:
                                normalized = ref_path.relative_to(project_root)
                                refs.append(Path(normalized))
                            except ValueError:
                                refs.append(ref_path)
                elif isinstance(value, (dict, list)):
                    find_refs(value)
        elif isinstance(obj, list):
            for item in obj:
                find_refs(item)
    
    find_refs(content)
    return refs


def build_dependency_graph() -> Dict[Path, List[Path]]:
    """依存関係グラフを構築"""
    graph = {}
    # スクリプトのディレクトリからプロジェクトルートに移動
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    schema_dir = project_root / "components/schemas"
    
    if not schema_dir.exists():
        print(f"Error: Schema directory '{schema_dir}' not found")
        return graph
    
    # 全YAMLファイルを処理
    for yaml_file in schema_dir.rglob("*.yaml"):
        # パスを正規化（プロジェクトルートからの相対パス）
        try:
            normalized_file = yaml_file.relative_to(project_root)
        except ValueError:
            normalized_file = yaml_file
            
        content = load_yaml_file(yaml_file)
        if content:
            refs = extract_refs(content, yaml_file, project_root)
            graph[Path(normalized_file)] = refs
            
    return graph


def detect_cycles(graph: Dict[Path, List[Path]]) -> List[List[Path]]:
    """循環参照を検出（単純なDFS）"""
    cycles = []
    
    def dfs(start: Path, current: Path, visited: List[Path]) -> None:
        if current in visited:
            # 循環を発見
            cycle_start = visited.index(current)
            cycle = visited[cycle_start:] + [current]
            # 重複チェック
            if cycle not in cycles:
                cycles.append(cycle)
            return
            
        # 現在のノードを訪問済みに追加
        new_visited = visited + [current]
        
        # 隣接ノードを探索
        for neighbor in graph.get(current, []):
            if neighbor in graph:  # グラフに存在するノードのみ
                dfs(start, neighbor, new_visited)
    
    # 全ノードから探索開始
    for node in graph:
        dfs(node, node, [])
            
    return cycles


def format_cycle(cycle: List[Path]) -> str:
    """循環参照を読みやすい形式で表示"""
    relative_paths = []
    for path in cycle:
        try:
            rel_path = path.relative_to(Path.cwd())
            relative_paths.append(str(rel_path))
        except ValueError:
            relative_paths.append(str(path))
    
    return " -> ".join(relative_paths)


def main():
    print("🔍 Checking for circular references in OpenAPI schemas...")
    print()
    
    # 依存関係グラフを構築
    graph = build_dependency_graph()
    
    if not graph:
        print("❌ No schema files found or all files failed to load")
        sys.exit(1)
    
    print(f"📁 Found {len(graph)} schema files")
    
    # 循環参照を検出
    cycles = detect_cycles(graph)
    
    if not cycles:
        print("✅ No circular references detected!")
        print()
        
        # 依存関係の要約を表示
        total_refs = sum(len(refs) for refs in graph.values())
        print(f"📊 Summary:")
        print(f"   - Schema files: {len(graph)}")
        print(f"   - Total references: {total_refs}")
        
        sys.exit(0)
    else:
        print(f"❌ Found {len(cycles)} circular reference(s):")
        print()
        
        for i, cycle in enumerate(cycles, 1):
            print(f"   {i}. {format_cycle(cycle)}")
        
        print()
        print("💡 To fix circular references:")
        print("   - Remove direct references between schemas")
        print("   - Use intermediate schemas (e.g., PostSummary)")
        print("   - Consider using allOf with partial schemas")
        
        sys.exit(1)


if __name__ == "__main__":
    main()