# OpenAPI 3.0 Structured Sample

## 1. 設計思想：なぜファイルを分割するのか

このリポジトリは、OpenAPI 3.0の定義を機能的に分割し、管理するためのためのサンプルです。単一の巨大なYAMLファイルでAPIを定義する代わりに、関心事（パス、コンポーネントなど）に基づいてファイルを分割し、`$ref`を用いてそれらを連携させます。

このアプローチには以下のメリットがあります。

- **保守性の向上**: 変更箇所が特定しやすくなり、複数人での開発時にコンフリクトのリスクが減少します。
- **可読性の向上**: 各ファイルが単一の役割に集中しているため、コードの見通しが良くなります。
- **再利用性の向上**: `User`や`Product`のような共通のデータモデルを一度定義すれば、複数のAPIエンドポイントから参照でき、定義の一貫性が保たれます。

---

## 2. ディレクトリ構造

プロジェクトは以下の構造で構成されています。

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

- **`root.yaml`**: API全体の「目次」です。APIの基本情報（タイトル、バージョン）と、すべてのAPIパスのリストを定義します。各パスの具体的な実装は`paths/`以下のファイルに委ねます。
- **`paths/**/*.yaml`**: 個々のAPIエンドポイント（例: `/users/{userId}`）に対する操作（`get`, `post`など）を定義します。これらの操作は`operations`というキーの下にまとめられます。
- **`components/schemas/**/*.yaml`**: `User`や`Post`といった、API全体で再利用されるデータモデル（スキーマ）を定義します。

---

## 3. 設計の核心：`$ref`による連携

この設計の鍵は`$ref`によるファイル間の連携です。3つの主要な参照パターンを理解することが重要です。

### パターン1: `root.yaml` → `paths/` (パス定義の参照)

`root.yaml`は、各APIパスの具体的な定義を`paths/`以下のファイルに委任します。参照先のファイル内にある`operations`オブジェクトを読み込むため、`$ref`の値は**`...yaml#/operations`**という形式になります。

**`root.yaml`**
```yaml
paths:
  /users/{userId}:
    # users__userId.yaml ファイル内の "operations" キーを指す
    $ref: "./paths/users/users__userId.yaml#/operations"
```

### パターン2: `paths/` → `components/` (スキーマの参照)

パス定義ファイルは、リクエストボディやレスポンスで使うデータモデルを`components/schemas/`以下のファイルから参照します。参照には**相対パス**と**JSONポインタ**を組み合わせます。

**`paths/users/users__userId.yaml`**
```yaml
operations:
  get:
    responses:
      '200':
        content:
          application/json:
            schema:
              # 1. 相対パスでファイルを探し
              # 2. JSONポインタ(#/User)でその中のキーを指す
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

## 4. ファイル作成ガイド（テンプレート）

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

**重要**: すべての操作 (`get`, `post`等) は `operations` キーで囲んでください。

```yaml
operations:
  get:
    operationId: getNewPath
    tags:
      - new
    summary: Get new path
    responses:
      '200':
        description: OK
        content:
          application/json:
            schema:
              # 必要に応じてコンポーネントを参照
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

## 5. コマンド

以下のコマンドを実行すると、分割されたすべてのYAMLファイルが検証され、単一の`resolved/openapi/openapi.yaml`ファイルにバンドル（結合）されます。

```console
# openapi.yaml を生成する
make gen
```

---

## Q&A

### Q: なぜ `operationId` ごと（`path + method` ごと）にファイルを分けなかったのですか？

**A:** OpenAPI 3.0では、`$ref`は仕様で許可された特定の場所でのみ使用でき、参照先で要素全体が完全に置き換えられます。Path Item Objectは`root.yaml`でパス全体を指す`$ref`を期待し、個々のHTTPメソッド（`get`など）では`$ref`を使用できません。そのため、パスごとにファイルを分け、その中で全HTTPメソッドを定義する現在の構造が、OpenAPI 3.0の仕様に準拠し、管理しやすい方法です。

**補足:** OpenAPI 3.1では`$ref`が他のプロパティと同階層に存在できるため、より柔軟な分割が可能です。

---

## 参考資料

- [OpenAPI Specification v3.0.2](https://spec.openapis.org/oas/v3.0.2)
