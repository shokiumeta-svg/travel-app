# AI Travel Planner 開発ドキュメント

- 最終更新: 2026-08-20
- 対象: 現在のReact + FastAPI + Docker Compose実装
- 開発段階: MVP

## 1. プロジェクト概要

旅行先、日程、人数、予算などの条件をもとに、特徴の異なる旅行プランを3案生成するWebアプリケーションである。

生成AIだけに旅行情報を推測させず、Google Places、Google Routes、Open-Meteoから取得したデータを組み合わせる。AIは主に観光地候補の選択、日別スケジュール、説明文、タイトル、概要、おすすめ理由を担当する。

距離、移動時間、費用合計はOpenAIへ自由に生成させず、Backendが外部APIの値とPythonの計算ロジックを使って決定する。

## 2. 現在実装されている機能

### 2.1 Frontend

- 旅行条件入力
  - 出発地
  - 目的地
  - 開始日
  - 終了日
  - 人数
  - 移動手段
  - 予算
  - 旅行スタイル
- 必須項目、日付順、人数、予算の入力検証
- FastAPIへのJSON送信
- API通信中のローディング画面
- 旅行プラン3案の比較カード表示
- 選択プランの詳細表示
- 日別タイムライン表示
- 区間ごとの移動手段、所要時間、距離表示
- 主な観光地と住所の表示
- 費用内訳と合計費用の表示
- 画面幅980px、680pxを基準にしたレスポンシブ表示
- `prefers-reduced-motion`への対応

### 2.2 Backend

- Pydanticによる入力検証
- Google Places APIから目的地の観光地候補取得
- Open-Meteoから天気予報取得
- OpenAIによる3つの日別旅行プラン生成
- AI出力の日付、件数、観光地、型の正規化
- Google Routes APIから実際の訪問順に経路取得
- Routes APIの所要時間を使ったスケジュール時刻補正
- 区間単位のRoutes失敗処理
- 旅行スタイルと実移動距離を使った費用計算
- 既存APIと外部APIテスト用エンドポイントの維持

## 3. MVPの対象外

- ホテル検索・予約
- 飲食店の価格検索・予約
- 航空券、鉄道運賃の正確な料金計算
- ユーザー登録、ログイン
- プランのDB保存、履歴、共有
- 地図表示、経路線の描画
- 複数通貨と海外タイムゾーン
- 本番環境へのデプロイ設定
- 高度なリトライ、レート制限、永続キャッシュ

## 4. システム構成

```text
Browser
  └─ React / App.jsx
       └─ fetch("http://localhost:8000/api/travel-plans")
            └─ FastAPI / app.main
                 └─ services/travel_plan.py
                      ├─ clients/places.py
                      ├─ clients/weather.py
                      ├─ clients/openai_client.py
                      └─ clients/routes.py
```

Docker Composeでは2つのサービスを起動する。

| Service | Runtime | Port | Role |
|---|---|---:|---|
| `frontend` | Node.js 24 / Vite / React | 5173 | UIとAPIリクエスト |
| `backend` | Python 3.12 / Uvicorn / FastAPI | 8000 | 検証、外部API統合、レスポンス生成 |

## 5. ディレクトリと責務

```text
travel-app/
├─ README.md
├─ compose.yaml
├─ .env
├─ docs/
│  └─ development.md
├─ frontend/
│  ├─ Dockerfile
│  ├─ package.json
│  ├─ vite.config.js
│  ├─ index.html
│  └─ src/
│     ├─ main.jsx
│     ├─ App.jsx
│     ├─ App.css
│     └─ index.css
└─ backend/
   ├─ Dockerfile
   ├─ requirements.txt
   ├─ app/
   │  ├─ main.py
   │  ├─ clients/
   │  │  ├─ places.py
   │  │  ├─ routes.py
   │  │  ├─ weather.py
   │  │  └─ openai_client.py
   │  └─ services/
   │     └─ travel_plan.py
   └─ tests/
      └─ test_travel_plan.py
```

### `backend/app/main.py`

- FastAPIアプリ生成
- CORS設定
- `TravelPlanRequest`定義
- URLと処理関数の対応付け
- Serviceの呼び出し

### `backend/app/clients/`

外部APIごとの認証、URL、HTTPリクエスト、基本的なエラー処理を担当する。

### `backend/app/services/travel_plan.py`

外部APIの呼び出し順、AI出力の検証、経路の紐付け、費用計算など、旅行プラン固有の処理を担当する。

### `frontend/src/App.jsx`

入力State、入力検証、API通信、画面遷移、プラン表示を担当する。現在は規模を抑えるため単一ファイル内に小さな表示コンポーネントを定義している。

## 6. Frontend設計

### 6.1 State

入力State:

| State | API field | 内容 |
|---|---|---|
| `origin` | `origin` | 出発地 |
| `destination` | `destination` | 目的地 |
| `startDate` | `start_date` | 開始日 |
| `endDate` | `end_date` | 終了日 |
| `travelers` | `travelers` | 人数 |
| `transportation` | `transportation` | 移動手段 |
| `budget` | `budget` | 予算 |
| `travelStyle` | `travel_style` | 旅行スタイル |

画面・通信State:

| State | 内容 |
|---|---|
| `plans` | APIから返された旅行プラン配列 |
| `loading` | API通信中かどうか |
| `error` | 入力または通信エラー文 |
| `screen` | `planner` / `results` / `detail` |
| `selectedPlanIndex` | 詳細表示中のプラン番号 |

### 6.2 画面遷移

React Routerはまだ導入していない。`screen` Stateによって同一ページ内の表示を切り替える。

```text
planner
  └─ API成功 → results
                  └─ プラン選択 → detail
                                      ├─ 戻る → results
                                      └─ 条件変更 → planner
```

入力画面へ戻っても入力Stateは保持される。再生成時には以前の`plans`を空にし、API成功後に新しい3案へ置き換える。

### 6.3 表示コンポーネント

| Component | Role |
|---|---|
| `ChoiceGroup` | 移動手段と旅行スタイルの選択 |
| `PlanCard` | 3案比較用の概要カード |
| `DaySchedule` | 1日分のタイムライン |
| `RouteDetails` | 移動手段、時間、距離 |
| `CostBreakdown` | 費用内訳と合計 |

表示データはAPIレスポンスから取得し、オブジェクトをJSXへ直接描画しない。`.map()`のkeyにはPlace ID、Plan ID、日付、インデックスを組み合わせた値を使用する。

### 6.4 UI方針

- 生成り色を背景に使用
- 深緑を主要色、柿色をアクセント色に使用
- 見出しにGeorgiaと明朝系フォントを使用
- 入力、比較、詳細を段階的に表示
- 詳細画面は日別旅程と費用内訳の2カラム
- 小さい画面では1カラム化
- ローディング表示は固定時間ではなく、実際の`fetch()`実行中だけ表示

## 7. Backend API設計

### 7.1 エンドポイント

| Method | Path | Role |
|---|---|---|
| GET | `/api/health` | Backend稼働確認 |
| POST | `/api/travel-plans` | 旅行プラン3案の生成 |
| GET | `/api/test/places` | Google Places疎通確認 |
| GET | `/api/test/routes` | Google Routes疎通確認 |
| GET | `/api/test/weather` | Open-Meteo疎通確認 |
| GET | `/api/test/openai` | OpenAI疎通確認 |

### 7.2 入力モデル

```json
{
  "origin": "横浜",
  "destination": "長野県伊那市",
  "start_date": "2026-09-12",
  "end_date": "2026-09-14",
  "travelers": 2,
  "transportation": "drive",
  "budget": 100000,
  "travel_style": "sightseeing"
}
```

Backendの検証規則:

- `origin`、`destination`: 1文字以上
- `travelers`: 1以上の整数
- `budget`: 0より大きい整数
- `end_date`: `start_date`以降
- `transportation`: `transit` / `drive` / `auto`
- `travel_style`: `sightseeing` / `budget` / `gourmet`

## 8. 旅行プラン生成フロー

`POST /api/travel-plans`は次の順番で処理する。

1. `main.py`がJSONを`TravelPlanRequest`へ変換・検証する
2. `create_travel_plan_data()`を呼び出す
3. `"{destination} 観光地"`でGoogle Placesを検索する
4. 候補が0件なら空の`plans`とメッセージを返す
5. 先頭6件をAIへ渡す候補にする
6. 最初の候補の座標でOpen-Meteoを呼ぶ
7. OpenAIへ条件、候補、天気を渡して日別プランを3案作る
8. BackendがAI出力を正規化する
9. 出発地をGoogle Placesで検索し、経路計算用の座標を取得する
10. 各日の位置情報を持つ予定間でGoogle Routesを呼ぶ
11. Routesの値を`days[].transportation[]`へ追加する
12. 実移動時間に対して到着予定が早すぎる場合は時刻を後ろへ補正する
13. Backendで費用内訳と合計を計算する
14. 内部処理用プロパティを除去し、JSONレスポンスを返す

## 9. OpenAIの責務

OpenAI Responses APIと`gpt-5-mini`を使用している。

OpenAIが担当するもの:

- 特徴の異なる3案の構成
- プランのタイトル
- summary
- recommendation reason
- 観光地候補の選択
- 日別スケジュール
- 観光地の説明
- 滞在時間の提案

OpenAIに生成させないもの:

- Routes APIの距離
- Routes APIの移動時間
- 交通費
- 宿泊費
- 食費
- 費用合計

プロンプトでは、Google Placesから渡したID・名称と完全に一致する観光地だけを使用するよう指示する。AIが候補外の`spot`を返した場合はBackendで除外する。

AI出力がJSONコードブロックで囲まれていた場合は囲みを除去して解析する。JSONとして解析できない場合はHTTP 500を返す。

## 10. AI出力の正規化

AI出力はそのままFrontendへ返さず、Backendで次の処理を行う。

- プラン数を3件にそろえる
- `plan_id`、タイトル、summaryの不足時にフォールバック値を設定する
- `start_date`から`end_date`までの日付をBackendで再作成する
- `days`件数を実際の旅行日数と一致させる
- `day`を1からの連番へ補正する
- 初日の先頭に出発地がなければ追加する
- 最終日の末尾に出発地への到着がなければ追加する
- `spot`はPlaces候補と一致するものだけを残す
- スケジュールが空ならPlaces候補を使った最低限の予定を作る
- 既存互換用の`main_spots`を実際に使用したPlaces候補から作る

## 11. Routes APIと移動情報

### 11.1 モード対応

| Input | Google Routes mode | Response mode |
|---|---|---|
| `drive` | `DRIVE` | `drive` |
| `transit` | `TRANSIT` | `transit` |
| `auto` | `DRIVE` | `drive` |

現在の`auto`はMVPとして車を選択する。

### 11.2 経路の作り方

AIが作った各日のスケジュールからPlace IDまたは出発地座標を持つ項目を抽出し、連続する地点間の経路を取得する。

同じリクエスト内で同一の出発地・到着地・モードが再登場した場合は、メモリ上のリクエスト内キャッシュを使用する。

### 11.3 部分失敗

Routes APIの失敗はプラン全体の失敗にしない。該当区間だけ次のようにする。

```json
{
  "from": "観光地A",
  "to": "観光地B",
  "mode": "drive",
  "duration_minutes": null,
  "distance_km": null,
  "route_available": false,
  "from_schedule_index": 1,
  "to_schedule_index": 2
}
```

`from_schedule_index`と`to_schedule_index`は、Frontendが経路表示を正しい予定の直後に配置するための補助値である。

### 11.4 時刻補正

Routes APIの移動時間が取れた場合、次の予定時刻が以下より早ければBackendが後ろへ補正する。

```text
次の予定の最短開始時刻
  = 現在の予定開始時刻
  + 現在の予定の滞在時間
  + Routes APIの移動時間
```

現状は日付をまたぐスケジュールへ変換せず、最大`23:59`へ収める。

## 12. 費用計算

費用は`backend/app/services/travel_plan.py`の定数とPython関数で計算する。

### 12.1 旅行スタイル別基準単価

| Style | 1人1泊 | 1人1食 | 1人1スポット | 1人1日その他 |
|---|---:|---:|---:|---:|
| `budget` | 6,000円 | 900円 | 700円 | 400円 |
| `sightseeing` | 9,000円 | 1,500円 | 1,200円 | 700円 |
| `gourmet` | 10,000円 | 2,500円 | 1,000円 | 800円 |

3案の概算に幅を持たせるため、宿泊、食事、観光、その他へ順に`0.9`、`1.0`、`1.1`の係数を適用する。

### 12.2 計算式

```text
宿泊費 = 1人1泊単価 × (旅行日数 - 1) × 人数 × プラン係数
食費   = 1人1食単価 × max(1, 旅行日数 × 3 - 2) × 人数 × プラン係数
観光費 = 1人1スポット単価 × spot件数 × 人数 × プラン係数
その他 = 1人1日単価 × 旅行日数 × 人数 × プラン係数
```

交通費:

- 車: Routesの総距離 × 30円/km
- 公共交通: Routesの総距離 × 20円/km × 人数
- 全経路が取得不可: 1,500円 × 旅行日数 × 人数
- 一部区間が取得不可: 取得不可1区間につき1,000円 × 人数を追加

各費目は100円単位へ丸める。

```text
estimated_cost
  = transportation
  + accommodation
  + food
  + activities
  + other
```

`estimated_cost`は必ず`cost_breakdown`の合計からBackendで作る。

## 13. レスポンス構造

```json
{
  "plans": [
    {
      "plan_id": "plan_1",
      "title": "歴史と自然を巡る旅",
      "summary": "2泊3日の旅行プランです。",
      "recommendation_reason": "景色と歴史をバランスよく楽しめます。",
      "estimated_cost": 43000,
      "cost_breakdown": {
        "transportation": 8000,
        "accommodation": 18000,
        "food": 9000,
        "activities": 3000,
        "other": 5000
      },
      "main_spots": [
        {
          "id": "google-place-id",
          "name": "観光地名",
          "address": "住所"
        }
      ],
      "days": [
        {
          "day": 1,
          "date": "2026-09-12",
          "schedule": [
            {
              "time": "08:00",
              "type": "departure",
              "name": "横浜",
              "description": "出発",
              "duration_minutes": null
            },
            {
              "time": "11:20",
              "type": "spot",
              "place_id": "google-place-id",
              "name": "観光地名",
              "description": "園内を観光します。",
              "duration_minutes": 100
            }
          ],
          "transportation": [
            {
              "from": "横浜",
              "to": "観光地名",
              "mode": "drive",
              "duration_minutes": 200,
              "distance_km": 210.0,
              "route_available": true,
              "from_schedule_index": 0,
              "to_schedule_index": 1
            }
          ]
        }
      ]
    }
  ]
}
```

上記の名称・数値は構造説明用であり、実際のレスポンスはユーザー入力と外部API結果によって変わる。

## 14. 外部APIクライアント

### 14.1 Google Places

- Endpoint: `https://places.googleapis.com/v1/places:searchText`
- Method: POST
- 認証: `GOOGLE_MAPS_API_KEY`
- 言語: 日本語
- 取得項目:
  - Place ID
  - 表示名
  - 住所
  - 緯度経度
- Timeout: 10秒

目的地の候補検索と、出発地の経路用座標取得に使用する。

### 14.2 Google Routes

- Endpoint: `https://routes.googleapis.com/directions/v2:computeRoutes`
- Method: POST
- 認証: `GOOGLE_MAPS_API_KEY`
- 取得項目:
  - duration
  - distanceMeters
- Timeout: 10秒

### 14.3 Open-Meteo

- Endpoint: `https://api.open-meteo.com/v1/forecast`
- Method: GET
- APIキー: 不要
- Timezone: `Asia/Tokyo`
- 取得項目:
  - weather code
  - 最高気温
  - 最低気温
  - 最大降水確率
- Timeout: 10秒

### 14.4 OpenAI

- SDK: OpenAI Python SDK
- API: Responses API
- Model: `gpt-5-mini`
- 認証: `OPENAI_API_KEY`

## 15. CORSと通信先

開発環境では次のオリジンを使用する。

| Component | Origin |
|---|---|
| Frontend | `http://localhost:5173` |
| Backend | `http://localhost:8000` |

FastAPIのCORSは`http://localhost:5173`を許可している。Frontendのfetch URLも`http://localhost:8000`へ固定されている。

本番化する場合は環境変数化し、本番FrontendのオリジンだけをCORSへ設定する。

## 16. Dockerと環境変数

`compose.yaml`は次の処理を行う。

- `backend/`をPythonコンテナとしてビルド
- `frontend/`をNode.jsコンテナとしてビルド
- Backendへルート`.env`を渡す
- ポート8000と5173をホストへ公開

必要な環境変数:

```dotenv
GOOGLE_MAPS_API_KEY=...
OPENAI_API_KEY=...
```

起動:

```bash
docker compose up --build
```

停止と再ビルド:

```bash
docker compose down
docker compose up --build
```

現在はソースコードのボリュームマウントがないため、コンテナへ変更を反映するには再ビルドが必要である。

## 17. エラー処理

| Situation | Current behavior |
|---|---|
| Frontend入力不足 | APIを呼ばず、日本語エラーを表示 |
| Backend入力不正 | FastAPI/Pydanticが422を返す |
| Places候補0件 | `plans: []`とメッセージを返す |
| Google APIキー未設定 | Backendが500を返す |
| OpenAI APIキー未設定 | Backendが500を返す |
| Places API失敗 | 外部APIのstatusと本文を返す |
| Weather API失敗 | 外部APIのstatusと本文を返す |
| OpenAI JSON解析失敗 | raw outputを含む500を返す |
| 出発地の座標取得失敗 | 経路を取得不可としてプラン生成を継続 |
| Routes API失敗 | 該当区間だけ`null`にして継続 |
| Frontend通信失敗 | 詳細をconsoleへ出し、画面には共通エラーを表示 |

## 18. テストと確認

### Frontend

```bash
cd frontend
npm run lint
npm run build
```

2026-08-20時点で、現在のUIに対してOxlintとVite production buildが成功している。

### Backend

`backend/tests/test_travel_plan.py`は標準ライブラリの`unittest`とモックを使用する。

```bash
cd backend
python -m unittest discover -s tests -v
```

テスト対象:

- 3プランへ正規化されること
- 入力期間と`days[].date`が一致すること
- Places候補外の観光地が除外されること
- Routesの一部失敗で全体が失敗しないこと
- 失敗区間の時間・距離が`null`になること
- `estimated_cost`と内訳合計が一致すること

現在のテストは外部APIを実際に呼ばない。実APIを使うE2Eテストは未実装である。

## 19. セキュリティ

- APIキーをFrontendへ渡さない
- APIキーをソースコード、ドキュメント、ログへ記載しない
- `.env`をGitへコミットしない
- Google APIキーにはAPI制限、利用上限などを設定する
- 本番ではCORS許可元を限定する
- 外部APIのエラー本文をそのまま一般ユーザーへ返さない設計を検討する

現在、プロジェクトルート用の`.gitignore`がないため、`.env`の誤コミット防止を今後の優先事項とする。

## 20. 現在の制約と既知の課題

1. ホテル情報がない
   - 宿泊施設名、正確な宿泊料金、宿泊地座標は扱えない
   - 日をまたぐ宿泊地から翌日の最初の観光地までの経路は取得しない

2. 費用は概算
   - 宿泊費、食費、観光費、その他は固定単価
   - 車の高速料金、駐車料金、燃費は未考慮
   - 公共交通の実運賃ではなく距離ベース

3. 予算は厳密な上限ではない
   - 入力予算はAIのプラン条件になるが、計算結果を予算内へ自動調整する処理はない

4. 時刻補正は単純化されている
   - 実移動時間で予定を後ろへずらすが、日付またぎや翌日への繰り越しは行わない

5. 外部APIの安定性
   - Routes以外は部分失敗として扱わず、リトライもない
   - HTTPクライアントをリクエストごとに生成する

6. API呼び出し回数
   - Routesは実際の訪問順に呼び出す
   - 同一リクエスト内キャッシュはあるが、リクエストをまたぐキャッシュはない

7. OpenAI呼び出し
   - 同期SDKをasync endpoint内から呼んでいるため、処理中にevent loopをブロックする可能性がある

8. Frontend構成
   - React Routerは未導入
   - `App.jsx`へ複数の表示コンポーネントがまとまっている
   - API URLがハードコードされている

9. データ永続化
   - DB、保存、共有、履歴はない

## 21. 今後の改善候補

優先度が高い順の候補:

1. ルート`.gitignore`と`.env.example`の追加
2. Frontend API URLとBackend CORSの環境変数化
3. 旅行日数の上限設定
4. WeatherとPlacesの部分失敗・リトライ設計
5. Backendレスポンス用Pydanticモデルの追加
6. OpenAI Structured Outputsの導入
7. OpenAIクライアントの非同期化
8. Routes呼び出し数の上限と永続キャッシュ
9. 宿泊施設・飲食店・実運賃APIの導入
10. 予算超過時の再構成ロジック
11. Reactコンポーネントの適度なファイル分割
12. React RouterまたはURLベースの画面遷移
13. Backend APIテストとブラウザE2Eテスト
14. DB保存、共有、認証
15. 本番デプロイ、監視、ログ設計

## 22. 更新履歴

| Date | Version | Summary |
|---|---|---|
| 2026-08-17 | 0.1 | 外部API単体疎通までの初版 |
| 2026-08-20 | 0.2 | 日別スケジュール、Routes紐付け、費用計算、3画面UIを含む現行実装へ全面更新 |
