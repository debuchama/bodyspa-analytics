# BODY SPA Analytics Dashboard

**bodyspa2008.com** のセラピスト出勤統計ダッシュボード

## 機能

- 🏠 **3店舗対応**: 千葉本店・新橋店・西葛西店
- 👤 **セラピスト統計**: 出勤日数・頻度・平均勤務時間・曜日パターン
- 📊 **ランキング**: 出勤日数・勤務時間・頻度のTOP10
- 📅 **週間スケジュール**: 4/18の週の出勤予定（公開後に更新）
- 🔮 **出勤予測**: 過去の曜日別パターンから出勤確率を推定
- 📈 **月別トレンド**: 全体・店舗別・セラピスト別の出勤推移

## データソース

[Sanity CMS](https://www.sanity.io/) API (GROQ) から直接取得

- `projectId`: 64ec3zln
- `dataset`: production

## 技術構成

| 要素 | 技術 |
|------|------|
| データ収集 | Python + Sanity GROQ API |
| ダッシュボード | 静的 HTML + Vanilla JS |
| ホスティング | GitHub Pages (`/docs`) |
| 自動更新 | GitHub Actions (毎日 JST 6:00) |

## ローカル実行

```bash
python scripts/collect_data.py
python scripts/export_data.py
# docs/index.html をブラウザで開く
```
