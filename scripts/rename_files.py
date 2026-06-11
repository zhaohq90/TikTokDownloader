#!/usr/bin/env python3
"""
重命名工具：将作品目录中的文件按新命名规则重新命名

旧格式: {date} {time}-{type}-{nickname}-{desc}.{ext}
        例: 2023-05-06 19.18.13-视频-云姑娘-描述.mp4

新格式: {date}_{time}_{id}_{type}.{ext}  (有ID时)
        {date}_{time}_{type}.{ext}        (无ID时)
        例: 2023-05-06_19.18.13_7123456789012345678_视频.mp4

用法:
  python rename_files.py           # 预览模式，只输出不执行
  python rename_files.py --execute # 实际执行重命名
"""

import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
VOLUME_DIR = PROJECT_DIR / "Volume"
DB_PATH = VOLUME_DIR / "Data" / "DetailData.db"
SETTINGS_PATH = VOLUME_DIR / "settings.json"

SKIP_DIRS = {"UID4253382337112871_喜喜_发布作品"}

ACCOUNT_DIR_RE = re.compile(r"^UID\d+_.+_发布作品$")

# 旧格式: 2023-05-06 19.18.13-视频-云姑娘-描述内容_1.jpeg
#   group(1) datetime   group(2) type   group(3) nickname
#   group(4) desc       group(5) index  group(6) ext
# desc 用非贪婪匹配，index 必须紧跟扩展名，避免 desc 中的 _N 被误判为 index
OLD_NAME_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2})"
    r"-(.+?)"
    r"-(.+?)"
    r"-(.+?)"
    r"(_\d+)?"
    r"\.(mp4|jpeg|jpg|png|webp)$"
)

# 新格式前缀: 2023-05-06_19.18.13
NEW_FORMAT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}\.\d{2}")


def load_settings():
    with open(SETTINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def find_db_table(db, dir_name):
    """通过 UID 匹配数据库表名（目录名和表名可能因特殊字符不完全一致）"""
    m = re.match(r"^UID(\d+)_", dir_name)
    uid = m.group(1) if m else ""
    if not uid:
        return dir_name
    tables = [t[0] for t in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    # 精确匹配优先
    if dir_name in tables:
        return dir_name
    # 通过 UID 匹配
    for t in tables:
        if uid in t:
            return t
    return dir_name


def build_db_lookup(db, table_name):
    """构建 (发布时间, 作品类型) -> [(作品ID, 作品描述), ...]"""
    try:
        rows = db.execute(
            f"SELECT DISTINCT 发布时间, 作品类型, 作品ID, 作品描述 FROM [{table_name}]"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    lookup = {}
    for pub_time, wtype, wid, wdesc in rows:
        lookup.setdefault((pub_time, wtype), []).append((wid, wdesc))
    return lookup


def find_work_id(lookup, datetime_str, file_type, desc):
    """从数据库查找作品ID，找不到返回 None"""
    db_datetime = datetime_str.replace(".", ":")
    candidates = lookup.get((db_datetime, file_type))
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0][0]
    # 多条匹配 — 用 desc 前30字符辅助定位
    if desc:
        for wid, db_desc in candidates:
            if db_desc and desc[:30] in db_desc:
                return wid
    return None


def generate_new_name(parsed, work_id, date_format, split):
    """按新规则生成文件名"""
    dt = datetime.strptime(parsed["datetime"], "%Y-%m-%d %H.%M.%S")
    new_time = dt.strftime(date_format)

    parts = [new_time]
    if work_id:
        parts.append(str(work_id))
    parts.append(parsed["type"])

    name = split.join(parts)
    if parsed["image_index"]:
        name += parsed["image_index"]
    return f"{name}.{parsed['ext']}"


def main():
    settings = load_settings()
    date_format = settings.get("date_format", "%Y-%m-%d_%H.%M.%S")
    split = settings.get("split", "_")
    execute = "--execute" in sys.argv

    db = sqlite3.connect(str(DB_PATH))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = VOLUME_DIR / f"rename_log_{timestamp}.txt"

    account_dirs = sorted(
        d
        for d in VOLUME_DIR.iterdir()
        if d.is_dir()
        and ACCOUNT_DIR_RE.match(d.name)
        and d.name not in SKIP_DIRS
    )

    ops = []
    stats = dict(matched=0, no_id=0, skipped=0, conflict=0, already_new=0)

    print(f"Accounts: {len(account_dirs)}")
    print(f"Format: date_format={date_format}, split={split}")
    print(f"Mode: {'EXECUTE' if execute else 'DRY RUN'}\n")

    for d in account_dirs:
        print(f"[{d.name}]")
        table_name = find_db_table(db, d.name)
        lookup = build_db_lookup(db, table_name)

        files = [f for f in d.iterdir() if f.is_file() and not f.name.startswith(".")]
        print(f"  Files: {len(files)}, DB keys: {len(lookup)}")

        used_names = set()

        for f in sorted(files, key=lambda x: x.name):
            # 已是新格式的跳过
            if NEW_FORMAT_RE.match(f.name):
                stats["already_new"] += 1
                continue

            m = OLD_NAME_RE.match(f.name)
            if not m:
                print(f"  [SKIP] {f.name}")
                ops.append((f, f, "SKIP: cannot parse"))
                stats["skipped"] += 1
                continue

            parsed = {
                "datetime": m.group(1),
                "type": m.group(2),
                "nickname": m.group(3),
                "desc": m.group(4),
                "image_index": m.group(5) or "",
                "ext": m.group(6),
            }

            wid = find_work_id(
                lookup, parsed["datetime"], parsed["type"], parsed["desc"]
            )
            new_name = generate_new_name(parsed, wid, date_format, split)
            new_path = f.parent / new_name

            # 目标文件已存在且不是自身
            if new_path.exists() and new_path.resolve() != f.resolve():
                print(f"  [CONFLICT] {f.name} -> {new_name}")
                ops.append((f, new_path, "CONFLICT: target exists"))
                stats["conflict"] += 1
                continue

            # 同一批次内重名（无ID时可能发生）
            if new_name in used_names:
                print(f"  [CONFLICT] {f.name} -> {new_name} (duplicate in batch)")
                ops.append((f, new_path, "CONFLICT: duplicate name"))
                stats["conflict"] += 1
                continue

            used_names.add(new_name)

            if wid:
                note = f"ID={wid}"
                stats["matched"] += 1
            else:
                note = "NO_ID"
                stats["no_id"] += 1

            print(f"  {f.name} -> {new_name} ({note})")
            ops.append((f, new_path, note))

    db.close()

    # 写日志
    with open(log_path, "w", encoding="utf-8") as lf:
        lf.write(f"Rename Log - {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        lf.write(f"date_format: {date_format}\n")
        lf.write(f"split: {split}\n")
        lf.write(f"mode: {'EXECUTE' if execute else 'DRY RUN'}\n")
        lf.write("=" * 80 + "\n\n")
        for old, new, note in ops:
            lf.write(f"DIR:  {old.parent.name}\n")
            lf.write(f"OLD:  {old.name}\n")
            lf.write(f"NEW:  {new.name}\n")
            lf.write(f"NOTE: {note}\n\n")

    total = stats["matched"] + stats["no_id"]
    print(f"\n--- Summary ---")
    print(f"Will rename: {total} (with ID: {stats['matched']}, no ID: {stats['no_id']})")
    print(f"Skipped: {stats['skipped']}, Conflicts: {stats['conflict']}, Already new: {stats['already_new']}")
    print(f"Log: {log_path}")

    if not execute:
        print("\nDRY RUN — use --execute to actually rename files.")
        return

    # 执行重命名
    done = 0
    errors = 0
    for old, new, note in ops:
        if note.startswith("SKIP") or note.startswith("CONFLICT"):
            continue
        try:
            old.rename(new)
            done += 1
        except OSError as e:
            print(f"  [ERROR] {old.name}: {e}")
            errors += 1
    print(f"\nRenamed: {done}, Errors: {errors}")


if __name__ == "__main__":
    main()
