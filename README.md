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

- **`root.yaml`**: API全体の「目次」。APIの基本情報（タイトル、バージョン）と、すべてのAPIパスのリストを定義しています。各パスの具体的な実装は`paths/`以下
- **`paths/**/*.yaml`**: 個々のAPIエンドポイント（例: `/users/{userId}`）に対する操作（`get`, `post`など）を定義しています。これらの操作は`operations`というキーの下にまとめられます。
- **`components/schemas/**/*.yaml`**: `User`や`Post`といった、API全体で再利用されるデータモデル（スキーマ）を定義しています。

---

## 2. `$ref`による連携

### パターン1: `root.yaml` → `paths/` (パス定義の参照)

`root.yaml`は、各APIパスの具体的な定義を`paths/`以下のファイルに委任します。
参照先のファイル内にある`operations`オブジェクトを読み込むため、`$ref`の値は**`...yaml#/operations`**という形式になります。

**`root.yaml`**
```yaml
paths:
  /users/{userId}:
    # users__userId.yaml ファイル内の "operations" キーを指す
    $ref: "./paths/users/users__userId.yaml#/operations"
```

### パターン2: `paths/` 内でのスキーマ定義と `components/` への参照

各パス定義ファイルは、リクエストボディとレスポンスのスキーマをファイル内で直接定義します。
これらのスキーマ名は、規約として **`[operationId]Request`** および **`[operationId]Response`** と命名します。

そして、その定義の中から`$ref`を使い、`components/schemas/`以下にある共通のデータモデルを参照します。これにより、パス固有のスキーマ定義と共通コンポーネントの再利用を両立させています。

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
      $ref: "../../components/schemas/users/User.yaml#/User"
```

### パターン3: `components/` → `components/` (スキーマ間の参照)

スキーマ定義ファイルが、別のスキーマを参照することもできます。これにより、複雑なデータモデルを部品のように組み合わせて定義できます。

**`components/schemas/users/User.yaml`**
```yaml
User:
  type: object
  properties:
    recentPosts:
      type: array
      items:
        # 同じディレクトリにある Post.yaml の Post キーを指す
        $ref: "./Post.yaml#/Post"
```

---

## 3. ファイル作成ガイド（テンプレート）

新しいAPIを追加する際のテンプレートです。

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

**重要**:
- すべての操作 (`get`, `post`等) は `operations` キーで囲んでください。
- リクエストボディとレスポンスのスキーマは、ファイル下部の`components`セクションで定義し、命名規則は **`[operationId]Request`** / **`[operationId]Response`** に従います。

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

# このファイル内で使用するリクエスト/レスポンスのスキーマを定義
components:
  schemas:
    CreateNewPathRequest:
      type: object
      properties:
        name:
          type: string
    CreateNewPathResponse:
      # 共通コンポーネントを参照
      $ref: "../../components/schemas/new/NewObject.yaml#/NewObject"
```

### Component Schema File (`components/schemas/[Tag]/...yaml`)

**重要**: ファイルのルートキーが、そのスキーマのコンポーネント名になります。

**`NewObject.yaml`**
```yaml
# このファイル名は NewObject.yaml
NewObject: # <--- ルートキーがスキーマ名
  type: object
  properties:
    id:
      type: string
    name:
      type: string
```

---

## 4. コマンド

### ファイルの結合 (Bundling)

分割されたすべてのYAMLファイルを検証し、単一の`resolved/openapi/openapi.yaml`ファイルにバンドル（結合）します。

```console
# openapi.yaml を生成する
make gen
```

### 単一ファイルの分解 (Decomposing)

逆に、単一の`openapi.yaml`ファイルをこのリポジトリの構造に分解するには、`decompose.py`スクリプトを使用します。

```console
# 例: single_openapi.yaml をカレントディレクトリに分解する
python decompose.py single_openapi.yaml --output .
```

---

## Q&A

### Q: なぜ `operationId` ごと（`path + method` ごと）にファイルを分けなかったのですか？

**A:** OpenAPI 3.0では、`$ref`は仕様で許可された特定の場所でのみ使用でき、参照先で要素全体が完全に置き換えられます。
Path Item Objectは`root.yaml`でパス全体を指す`$ref`を期待し、個々のHTTPメソッド（`get`など）では`$ref`を使用できません。
そのため、パスごとにファイルを分け、その中で全HTTPメソッドを定義する現在の構造が、OpenAPI 3.0の仕様に準拠し、管理しやすい方法です。

**補足:** OpenAPI 3.1では`$ref`が他のプロパティと同階層に存在できるため、より柔軟な分割が可能です。

---

## 参考資料

- [OpenAPI Specification v3.0.2](https://spec.openapis.org/oas/v3.0.2)
