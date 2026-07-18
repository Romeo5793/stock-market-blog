# note 公開ランブック（Agent / 手動共通）

マガジン: https://note.com/merry_orca9232/m/m471c1317cc4e  
名前: **株価調査メモ（週次）**

---

## 前提
- `docs/drafts/pending/manifest.json` が `status: pending`
- 原稿: `note-issue-XX-paid.txt` / `note-issue-XX-free.txt`
- Cursor ブラウザで note にログイン済み

---

## A. 有料記事

1. https://note.com/notes/new → 新規
2. タイトル・本文を貼る（「公開設定メモ」「X投稿用」は貼らない）
3. **公開に進む**
4. 記事タイプ: **有料** / 価格: **980**
5. 有料エリア: 導入〜免責（`---` の手前）まで無料、以降を有料
6. **マガジン（必須）**
   - 「マガジン」にチェック
   - **「株価調査メモ（週次）」の「追加」を押す** ← ここを飛ばさない
   - チェックだけ・「追加」未クリックだとマガジンに入らない
7. **投稿する**
8. 公開URLを控える（例: `https://note.com/merry_orca9232/n/n........`）

---

## B. 無料ダイジェスト

1. 再度 https://note.com/notes/new
2. 本文の「有料記事URLを貼ってください」を **AのURL** に置換
3. 公開に進む → **無料**
4. **同じくマガジン「追加」を押す**
5. 投稿する
6. 無料URLを控える

---

## C. 完了確認

1. マガジンページを開き、無料・有料の両方が並んでいるか見る
2. 無ければ各記事の編集画面からマガジン追加
3. 両方確認できたら:

```bash
cd ~/Projects/stock-market-blog
python3 scripts/sync_note_pending.py --mark-published
git add docs/drafts/pending/manifest.json && git commit -m "docs: mark note issue N as published." && git push
```

---

## Agent 向けショートカット

ユーザーが「READY_FOR_AGENT の手順で note 公開して」と言ったら、このランブックどおりに実行する。  
特に **マガジンの「追加」クリック** と **投稿後のマガジン一覧確認** を省略しない。
