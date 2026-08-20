# AI Travel Planner

旅行条件と外部APIの実データを組み合わせ、特徴の異なる旅行プランを3案生成するWebアプリです。

Reactで旅行条件を入力し、FastAPIがGoogle Places、Google Routes、Open-Meteo、OpenAIを連携して、日別スケジュール、移動時間・距離、費用内訳を返します。

## 主な機能

- 出発地、目的地、旅行日程、人数、予算、移動手段、旅行スタイルの入力
- Google Places APIによる実在する観光地候補の取得
- Google Routes APIによる区間ごとの所要時間・距離の取得
- Open-Meteoによる目的地周辺の天気情報取得
- OpenAIによる特徴の異なる旅行プラン3案の構成
- 入力期間と一致する日別スケジュールの生成
- Pythonのルールベース処理による費用内訳と合計費用の計算
- 入力、3案比較、選択プラン詳細の画面遷移
- PC、タブレット、スマートフォン向けのレスポンシブ表示

## システム構成

```text
ブラウザ
  └─ React + Vite（localhost:5173）
       └─ POST /api/travel-plans
            └─ FastAPI + Uvicorn（localhost:8000）
                 ├─ Google Places API
                 ├─ Open-Meteo API
                 ├─ OpenAI API
                 └─ Google Routes API
```

処理の流れは次のとおりです。

1. Reactが入力値を検証してFastAPIへ送信する
2. FastAPI/Pydanticがリクエストを再検証する
3. Google Placesから目的地の観光地候補を最大6件取得する
4. 最初の観光地の座標を使ってOpen-Meteoから天気を取得する
5. OpenAIが候補内の観光地だけを使って3案の日別構成を作る
6. Backendが日付、観光地、件数などを検証・補正する
7. 各プランの訪問順にGoogle Routesから経路情報を取得する
8. Backendが移動時間に合わせて時刻を補正し、費用を計算する
9. Reactが3案の比較カードと選択プランの詳細を表示する

## ファイル構成

```text
travel-app/
├─ README.md                         # プロジェクト全体の案内
├─ compose.yaml                      # Frontend/BackendのDocker Compose設定
├─ .env                              # APIキー（Gitへコミットしない）
├─ docs/
│  └─ development.md                 # 実装・設計・開発状況の詳細
├─ frontend/
│  ├─ Dockerfile                     # Node.js/Viteコンテナ
│  ├─ package.json                   # npm scriptsと依存パッケージ
│  ├─ package-lock.json              # npm依存関係の固定情報
│  ├─ vite.config.js                 # Vite設定
│  ├─ index.html                     # Reactを配置するHTML入口
│  ├─ public/                        # faviconなどの静的ファイル
│  └─ src/
│     ├─ main.jsx                    # Reactアプリのマウント処理
│     ├─ App.jsx                     # 入力、API通信、画面遷移、結果表示
│     ├─ App.css                     # 画面固有のレイアウトとレスポンシブCSS
│     ├─ index.css                   # 共通色、フォント、基本スタイル
│     └─ assets/                     # 画像アセット
└─ backend/
   ├─ Dockerfile                     # Python/FastAPIコンテナ
   ├─ requirements.txt               # Python依存パッケージ
   ├─ app/
   │  ├─ main.py                     # FastAPIアプリ、CORS、入力モデル、API定義
   │  ├─ services/
   │  │  └─ travel_plan.py           # 外部API統合、正規化、経路付与、費用計算
   │  └─ clients/
   │     ├─ places.py                # Google Places APIクライアント
   │     ├─ routes.py                # Google Routes APIクライアント
   │     ├─ weather.py               # Open-Meteo APIクライアント
   │     └─ openai_client.py         # OpenAI APIクライアントとプロンプト
   └─ tests/
      └─ test_travel_plan.py         # 外部APIをモック化した統合テスト
```

`frontend/node_modules/`、`frontend/dist/`、`__pycache__/`は生成物のため、上の構成図では省略しています。

## 技術スタック

### Frontend

- React 19
- Vite 8
- JavaScript / JSX
- CSS
- Oxlint

### Backend

- Python 3.12
- FastAPI
- Uvicorn
- Pydantic
- httpx
- OpenAI Python SDK

### 外部サービス

- Google Places API (New)
- Google Routes API
- Open-Meteo
- OpenAI Responses API

## 環境変数

プロジェクトルートの`.env`へ次のキーを設定します。

```dotenv
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
OPENAI_API_KEY=your_openai_api_key
```

`.env`はBackendコンテナだけに渡されます。APIキーをFrontendへ渡したり、ソースコードへ直接記載したりしないでください。

## Dockerでの起動

プロジェクトルートで実行します。

```bash
docker compose up --build
```

起動後のURL:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

停止:

```bash
docker compose down
```

現在のCompose設定にはソースコードのボリュームマウントがないため、コード変更後は再ビルドしてください。

```bash
docker compose down
docker compose up --build
```

## ローカルで個別に起動する場合

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
python -m venv .venv
```

仮想環境を有効化した後:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API

| Method | Path | 用途 |
|---|---|---|
| GET | `/api/health` | Backendの稼働確認 |
| POST | `/api/travel-plans` | 旅行条件から3つのプランを生成 |
| GET | `/api/test/places` | Google Placesの疎通確認 |
| GET | `/api/test/routes` | Google Routesの疎通確認 |
| GET | `/api/test/weather` | Open-Meteoの疎通確認 |
| GET | `/api/test/openai` | OpenAIの疎通確認 |

### `POST /api/travel-plans`の入力

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

選択値:

- `transportation`: `drive` / `transit` / `auto`
- `travel_style`: `sightseeing` / `budget` / `gourmet`

### 主なレスポンス項目

```text
plans[]
├─ plan_id
├─ title
├─ summary
├─ recommendation_reason
├─ estimated_cost
├─ cost_breakdown
│  ├─ transportation
│  ├─ accommodation
│  ├─ food
│  ├─ activities
│  └─ other
├─ main_spots[]
└─ days[]
   ├─ day
   ├─ date
   ├─ schedule[]
   │  ├─ time
   │  ├─ type
   │  ├─ name
   │  ├─ description
   │  └─ duration_minutes
   └─ transportation[]
      ├─ from / to
      ├─ mode
      ├─ duration_minutes
      ├─ distance_km
      └─ route_available
```

詳細なレスポンス例と計算規則は[開発ドキュメント](docs/development.md)を参照してください。

## 確認コマンド

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Backendのモック統合テスト:

```bash
cd backend
python -m unittest discover -s tests -v
```

テストでは外部APIを実際に呼ばず、3案生成、日付補正、架空観光地の除外、経路の部分失敗、費用合計の一致を確認します。

## 現在の制約

- ホテル、飲食店、料金専用APIは未導入
- 宿泊費、食費、観光費、その他はBackendの基準単価による概算
- 宿泊施設の座標がないため、宿泊地を含む日またぎ経路は未対応
- Routes APIで取得できない区間は`null`とフォールバック交通費で処理
- FrontendのBackend URLとCORS許可元はlocalhost固定
- DB、ユーザー認証、プラン保存・共有機能は未実装
- 外部API全体の再試行、レート制限、キャッシュは未実装

## 開発資料

設計、責務分担、費用計算、エラー処理、実装状況については[docs/development.md](docs/development.md)を参照してください。
