# OpenAPI 3.0 Structured Sample

OpenAPI 3.0の定義を機能的に分割し、管理するためのためのサンプルレポジトリ

## 1. ディレクトリ構造

```
|- root.yaml           # API定義全体のエントリーポイント
|- paths/              # 各APIパスの操作(get, post等)を定義
|   `- users/
|   `- products/
|- components/         # 再利用可能なコンポーネントを定義
|   `- schemas/        # データモデル(スキーマ)を定義
|       `- users/
|       `- products/
|- Makefile            # 分割されたYAMLを1つに束ねるコマンド
`- README.md           # このファイル
```

### 各ファイルの役割

- **`root.yaml`**: API全体のエントリーポイント。基本情報とパス一覧
- **`paths/**/*.yaml`**: 各エンドポイントの操作を`operations`キーで定義
- **`components/schemas/**/*.yaml`**: 再利用可能なデータモデル

---

## 2. `$ref`による連携

### パターン1: `root.yaml` → `paths/`

`root.yaml`がパス定義を`paths/`ファイルに委任。`$ref`は`...yaml#/operations`形式。

**`root.yaml`**
```yaml
paths:
  /users/{userId}:
    # users__userId.yaml ファイル内の "operations" キーを指す
    $ref: "./paths/users/users__userId.yaml#/operations"
```

### パターン2: `paths/` → `components/`

パスファイル内でリクエスト/レスポンススキーマを定義し、共通コンポーネントを参照。命名規則: `[operationId]Request/Response`

**`paths/users/users__userId.yaml`**
```yaml
operations:
  get:
    operationId: getUserById
    responses:
      '200':
        content:
          application/json:
            schema:
              # 1. 同じファイル内のcomponentsセクションを参照
              $ref: "#/components/schemas/GetUserByIdResponse"
# 同じファイル内にcomponentsセクションを定義
components:
  schemas:
    # operationId に基づいて命名
    GetUserByIdResponse:
      # 2. 共通コンポーネントを相対パスで参照
      $ref: "../../components/schemas/users/User.yaml"
```

### パターン3: `components/` → `components/`

スキーマ間の相互参照でデータモデルを組み合わせ。

**`components/schemas/users/User.yaml`**
```yaml
type: object
properties:
  recentPosts:
    type: array
    items:
      # 同じディレクトリにある Post.yaml を指す
      $ref: "./Post.yaml"
```

---

## 3. ファイル作成ガイド

### `root.yaml`

```yaml
openapi: 3.0.2
info:
  title: Sample API
  version: 1.0.0
paths:
  # ... 既存のパス ...
  /new/path:
    $ref: "./paths/new/new_path.yaml#/operations"
```

### Path File (`paths/[Tag]/...yaml`)

**重要**: 操作は`operations`キーで囲む。スキーマは`[operationId]Request/Response`で命名。

```yaml
operations:
  post:
    operationId: createNewPath
    tags:
      - new
    summary: Create a new resource
    requestBody:
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/CreateNewPathRequest"
    responses:
      '200':
        description: OK
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CreateNewPathResponse"

# ローカルスキーマ定義
components:
  schemas:
    CreateNewPathRequest:
      type: object
      properties:
        name:
          type: string
    CreateNewPathResponse:
      # 共通コンポーネントを参照
      $ref: "../../components/schemas/new/NewObject.yaml"
```

### Component Schema File (`components/schemas/[Tag]/...yaml`)

**重要**: ファイルのルートキーがコンポーネント名。

**`NewObject.yaml`**
```yaml
# このファイル名は NewObject.yaml
type: object
properties:
  id:
    type: string
  name:
    type: string
```

---

## 4. コマンド

```console
# 分割されたYAMLファイルを単一のopenapi.yamlに結合
make gen

# 全YAMLファイルをフォーマット
make format

# OpenAPI仕様をRedoclyでリント
make lint

# スキーマファイル間の循環参照を検出
make check-circular

# 単一のOpenAPIファイルをこのリポジトリ構造に分解
python scripts/decompose.py single_openapi.yaml --output .
```

## Q&A

### Q1: なぜ `operationId` ごと（`path + method` ごと）にファイルを分けなかったのですか？

**A:** OpenAPI 3.0では`$ref`が特定の場所でのみ使用可能。個別のHTTPメソッドでは`$ref`を使えないため、パスごとにファイルを分割する構造を採用。

**補足:** OpenAPI 3.1では`$ref`がより柔軟に使用可能。

### Q2: 循環参照とは何ですか？どのような問題が発生しますか？

**A:** スキーマファイル間で相互参照する状態。`User.yaml` ↔ `Post.yaml`など。

**問題:** `User_1`, `Post_1`などの重複スキーマが生成される

**検出方法:** `make check-circular`

**解決:**
- 一方向参照にする
- 中間スキーマ作成（`PostSummary.yaml`など）
- `allOf`で部分的に拡張

---


## 参考資料

- [OpenAPI Specification v3.0.2](https://spec.openapis.org/oas/v3.0.2)
