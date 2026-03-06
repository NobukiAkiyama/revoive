# Resolve Voice Replace Extension v2.11 — PySide6 内部優先版

**バージョン:** 2.11（内部起動優先・Free版最適化）  
**更新日:** 2026年3月3日  
**ベース:** v2.1（PySide6 移行案）  
**開発状況:** バックエンド完了 / ブリッジ復旧済み / UI 統合中

---

## 1. 解決方針：内部優先ブリッジの確立

Free版 DaVinci Resolve において、外部プロセスからの接続（External API）は不安定かつ制限が多いため、**Resolve のメニュー（Workspace -> Scripts -> Utility）から Python を起動する方式**を最優先とします。

### 1.1 内部起動のメリット
- **API 制限の回避**: Resolve が自身で起動した Python プロセス内では、`resolve` オブジェクトが自動的にグローバル変数として提供されるため、接続失敗（None）が発生しない。
- **Free版完全対応**: 外部アタッチ機能がロックされている Free版環境でも 100% 確実に動作する。

---

## 2. 統合基盤の再定義

### 2.1 連携ブリッジ (`extension/resolve_api.py`)
- **優先取得ロジック**:
    1. 起動スクリプトから渡された `resolve` オブジェクトを最優先で使用。
    2. `__main__` モジュール内のグローバルな `resolve` 変数を探索。
    3. 最終フォールバックとして `fusionscript.dll` による外部アタッチを試行。

### 2.2 起動用ランチャースクリプト (`ReVoice_Launcher.py`)
Resolve のスクリプトディレクトリに配置する、PySide6 アプリを呼び出すための「薄い」エントリーポイント。
- **役割**: Resolve 内の `resolve` 変数を掴み、`app_entry.main(resolve)` へ「バケツリレー」する。

---

## 3. PySide6 アプリケーション構成

### 3.1 起動シーケンス (内部優先版)
1. **Resolve メニューから起動**: ユーザーがメニューを選択。
2. **ランチャー実行**: `ReVoice_Launcher.py` が `resolve` オブジェクトを保持。
3. **App 起動**: `app_entry.py` の `main` 関数へ `resolve` が渡され、PySide6 ウィンドウが起動。
4. **接続完了**: UI 上で即座に `[OK] Connected to Resolve` と表示される。

### 3.2 UI コンポーネント (非同期設計)
- **`ui/gui_panel_generate.py`**: `QThread` を使用し、配置処理中も UI をフリーズさせない。
- **`ui/worker_process.py`**: `external_processor.py` との標準入出力通信を非同期で行う。

---

## 4. 開発ロードマップ

### Day 1: 内部ブリッジの正常化（完了）
- [x] `extension/resolve_api.py` の内部優先化。
- [x] `app_entry.py` の引数対応（`resolve_obj` の受け取り）。
- [x] `extension/audio_export.py` の実装（レンダープリセット経由）。

### Day 2-3: UI コンポーネントの刷新
- [x] `GeneratePanel` の PySide6 / QThread 化。
- [ ] `AnalyzePanel` の刷新（`audio_export` 連携）。
- [ ] `ReviewPanel` の刷新（`QTableWidget` 実装）。

---

## 5. 技術的アドバイス（Free版・内部起動特化）

- **QApplication の衝突回避**:
  Resolve は内部に独自の Qt イベントループを持っている場合があるため、`QApplication.instance()` を使用して二重起動を防止すること。
- **sys.exit の扱い**:
  内部起動時に `sys.exit()` を呼ぶと、Resolve ごと終了してしまうリスクがあるため、`app.exec()` の戻り値のみを扱うように設計する。
- **パスの解決**:
  `%PROGRAMDATA%` 以下のスクリプトからデスクトップ上の `extension/` を呼べるよう、起動時に `sys.path` を動的に追加する処理を徹底する。

---

## 6. ファイル構成

```
davinchi-voice-replace/
├── processor/                        ← ✅ 完了（AI パイプライン）
├── extension/
│   ├── resolve_api.py                ← ✅ 完了（内部優先ブリッジ）
│   ├── audio_export.py               ← ✅ 完了（音声抽出）
│   └── track_builder.py              ← ✅ 完了（自動配置エンジン）
├── ui/
│   ├── app_entry.py                  ← ⚡ 修正（メインウィンドウ）
│   ├── gui_panel_generate.py         ← ✅ 完了（配置パネル）
│   └── gui_panel_*.py                ← 🔍 順次 PySide6 化
└── ReVoice_Launcher.py               ← ✨ 新設（Resolve スクリプトフォルダ用）
```
