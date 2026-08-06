#!/usr/bin/env python3
"""
JSON配列ファイルを origin/<branch> と衝突なくマージしてpushするヘルパー。

## なぜこれが必要か
これまでは `git stash → git pull --rebase → git stash pop` で
posted_items.json / all_products.json のような「複数のワークフロー・cron
ジョブから同時に更新されうるJSON配列」を同期していた。
このやり方だとテキストレベルの3-wayマージが行われるため、同じ行（配列全体が
1行のJSONだと配列全体）が両側で変わっただけで衝突し、
`<<<<<<< / ======= / >>>>>>>` のコンフリクトマーカーがそのままファイルに
残った状態でコミット・pushされる事故が起きた（2026-08-04〜08-06に実際発生し、
posted_items.jsonが2日間壊れて投稿が止まった）。壊れたJSONは
`json.load()` で読めなくなり、以降の処理が全て失敗する。

## このスクリプトの安全性
git のテキストマージ機能（merge / rebase / stash pop）を一切使わない。
- リモートの内容は `git show origin/<branch>:<file>` で読むだけ（作業ツリーに触れない）
- マージはPythonの集合演算で行う（--mode merge の場合。dict配列は --key で重複排除）
- push が非fast-forwardで失敗したら `git reset --soft origin/<branch>` で
  コミットの親を最新のリモートに付け替えるだけ（作業ツリー・他の追跡ファイルには
  一切触れない）
上記のいずれも3-wayテキストマージを伴わないため、コンフリクトマーカーが
混入する余地がない。

## 使い方
  python3 scripts/git_sync_json.py posted_items.json --mode merge --limit 1000 \\
      --message "update posted items [skip ci]"

  python3 scripts/git_sync_json.py products.json --mode overwrite \\
      --message "update products 2026-08-06"

  python3 scripts/git_sync_json.py link-page/all_products.json \\
      --mode merge --key item_code --limit 300 --message "update all_products [skip ci]"

--mode merge     : ローカルとリモートの配列を要素単位で和集合にする（重複排除）。
                    --key を指定すると dict 配列を key の値で重複排除する。
--mode overwrite : リモートの内容は見ずローカルの内容を常に採用する
                    （products.json のように「その日の内容で完全に置き換える」
                    ファイル向け）。
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True)


def try_parse(text: str):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def dedupe_key(item, key: str | None):
    if key is not None and isinstance(item, dict):
        return item.get(key)
    if isinstance(item, (str, int, float, bool)) or item is None:
        return item
    return json.dumps(item, sort_keys=True, ensure_ascii=False)


def union(local_items: list, remote_items: list, key: str | None) -> list:
    """local_itemsを優先しつつ、remoteにしかない要素も残す和集合。"""
    seen = set()
    merged = []
    for item in local_items + remote_items:
        k = dedupe_key(item, key)
        if k in seen:
            continue
        seen.add(k)
        merged.append(item)
    return merged


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("file")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--mode", choices=["merge", "overwrite"], default="merge")
    ap.add_argument("--key", default=None, help="--mode merge で dict 配列を重複排除するキー")
    ap.add_argument("--limit", type=int, default=None, help="マージ後に末尾から残す件数")
    ap.add_argument("--message", required=True)
    ap.add_argument("--max-attempts", type=int, default=5)
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"[git_sync_json] {path} が存在しないためスキップします")
        return

    local_data = try_parse(path.read_text(encoding="utf-8"))
    if local_data is None:
        print(f"[git_sync_json] エラー: ローカルの {path} がJSONとして不正です。中断します。")
        sys.exit(1)

    for attempt in range(1, args.max_attempts + 1):
        run(["git", "fetch", "origin", args.branch])

        if args.mode == "merge":
            remote_show = run(["git", "show", f"origin/{args.branch}:{args.file}"])
            remote_data = try_parse(remote_show.stdout) if remote_show.returncode == 0 else []
            if remote_data is None:
                print(f"[git_sync_json] 警告: リモートの {args.file} がJSON不正のため無視します")
                remote_data = []
            merged = union(local_data, remote_data, args.key)
            if args.limit:
                merged = merged[-args.limit:]
        else:
            merged = local_data

        path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2 if args.key else None) + "\n",
            encoding="utf-8",
        )

        run(["git", "add", args.file])
        if run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
            print(f"[git_sync_json] {args.file} に変更なし")
            return

        run(["git", "commit", "-m", args.message])
        push = run(["git", "push", "origin", f"HEAD:{args.branch}"])
        if push.returncode == 0:
            print(f"[git_sync_json] {args.file} をpushしました（{attempt}回目で成功）")
            return

        print(
            f"[git_sync_json] push失敗（{attempt}/{args.max_attempts}回目）。"
            f"origin/{args.branch} に追従してリトライします: {push.stderr.strip()[:200]}"
        )
        run(["git", "reset", "--soft", f"origin/{args.branch}"])
        time.sleep(2)

    print(f"[git_sync_json] {args.file} のpushに{args.max_attempts}回失敗しました。手動確認してください。")
    sys.exit(1)


if __name__ == "__main__":
    main()
