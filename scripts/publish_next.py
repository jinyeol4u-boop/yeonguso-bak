#!/usr/bin/env python3
"""
queue/queue.json 에서 다음 글 1편을 꺼내:
1) posts/ 에 실제 글 파일로 배치
2) 해당 카테고리 페이지(categories/*.html) 목록 맨 위에 링크 추가
3) 랜딩페이지(index.html)의 해당 카테고리 "최근 글" 카드를 최신 글로 교체
4) queue.json 에서 처리한 항목 제거, 원본 큐 파일 삭제

GitHub Actions가 매일 지정된 시각(cron)에 이 스크립트를 실행하고,
바뀐 파일들을 자동으로 commit & push 합니다.
큐가 비어있으면 아무 것도 하지 않고 조용히 종료합니다(정상 종료, exit 0).
"""
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE_PATH = os.path.join(ROOT, "queue", "queue.json")

ROW_TEMPLATE_CATEGORY = '''    <a href="/{target}" class="row">
      <span class="r-body">
        <span class="r-name">{title}</span>
        <span class="r-desc">{desc}</span>
        <span class="r-meta">{date} · Ironbee</span>
      </span>
      <span class="r-arrow">›</span>
    </a>
'''

ROW_TEMPLATE_INDEX = '''<a href="/{target}" class="row post-row">
          <span class="r-body">
            <span class="r-tag">{tag}</span>
            <span class="r-name">{title}</span>
            <span class="r-desc">{desc}</span>
            <span class="r-meta">{date} · Ironbee</span>
          </span>
          <span class="r-arrow">›</span>
        </a>'''


def kst_today_str():
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime("%Y.%m.%d")


def load_queue():
    with open(QUEUE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_queue(items):
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def publish_post(entry, date_str):
    content_path = os.path.join(ROOT, entry["content_file"])
    target_path = os.path.join(ROOT, entry["target"])
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(content_path, encoding="utf-8") as f:
        content = f.read()
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.remove(content_path)
    print(f"[publish] {entry['content_file']} -> {entry['target']}")


def update_category_page(entry, date_str):
    cat_path = os.path.join(ROOT, entry["category_file"])
    with open(cat_path, encoding="utf-8") as f:
        content = f.read()

    new_row = ROW_TEMPLATE_CATEGORY.format(
        target=entry["target"], title=entry["title"], desc=entry["desc"], date=date_str
    )

    empty_pattern = r'<div class="empty">.*?</div>\s*'
    if re.search(empty_pattern, content, re.S):
        content = re.sub(empty_pattern, new_row, content, count=1, flags=re.S)
    else:
        content = content.replace(
            '<div class="row-list">\n', '<div class="row-list">\n' + new_row, 1
        )

    with open(cat_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[category] updated {entry['category_file']}")


def update_index_card(entry, date_str):
    index_path = os.path.join(ROOT, "index.html")
    with open(index_path, encoding="utf-8") as f:
        content = f.read()

    tag = re.escape(entry["category_tag"])
    pattern = (
        r'<a href="[^"]*" class="row post-row">\s*'
        r'<span class="r-body">\s*'
        r'<span class="r-tag">' + tag + r'</span>.*?</a>'
    )
    new_block = ROW_TEMPLATE_INDEX.format(
        target=entry["target"], tag=entry["category_tag"], title=entry["title"],
        desc=entry["desc"], date=date_str
    )

    if re.search(pattern, content, re.S):
        content = re.sub(pattern, new_block, content, count=1, flags=re.S)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[index] updated card for {entry['category_tag']}")
    else:
        print(f"[index] WARNING: no matching card found for tag {entry['category_tag']!r}; skipped")


def main():
    if not os.path.exists(QUEUE_PATH):
        print("queue.json not found — nothing to do.")
        return 0

    items = load_queue()
    if not items:
        print("Queue is empty — nothing to publish today.")
        return 0

    entry = items[0]
    remaining = items[1:]
    date_str = kst_today_str()

    publish_post(entry, date_str)
    update_category_page(entry, date_str)
    update_index_card(entry, date_str)
    save_queue(remaining)

    print(f"Done. {len(remaining)} item(s) left in queue.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
