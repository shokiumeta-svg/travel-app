# AI Travel Planner Frontend

AI Travel PlannerのReact + Viteフロントエンドです。

プロジェクト全体の構成、Dockerでの起動方法、API仕様は[ルートREADME](../README.md)を参照してください。詳細な設計と現在の開発状況は[開発ドキュメント](../docs/development.md)に記載しています。

## 担当範囲

- 旅行条件の入力と検証
- `POST /api/travel-plans`へのリクエスト
- API通信中のローディング表示
- 旅行プラン3案の比較
- 選択プランの日別スケジュール表示
- 移動時間、距離、費用内訳の表示
- レスポンシブUI

## 開発コマンド

```bash
npm install
npm run dev
```

確認:

```bash
npm run lint
npm run build
```

開発サーバーは通常`http://localhost:5173`で起動し、Backendの`http://localhost:8000`へアクセスします。
