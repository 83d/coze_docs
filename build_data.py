#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扣子官方文档 - 数据构建集成脚本

完整流程：
1. 运行 nav_scraper/gen_nav_catalog.py 生成最新的"导航栏目录.md"
2. 解析"导航栏目录.md"，提取所有页面条目（编号、名称、URL）
3. 创建 data/ 目录结构（按分区分文件夹）
4. 批量爬取所有页面，复用浏览器实例提高效率
5. 将 Markdown 文件按目录结构保存到 data/ 文件夹

依赖：
- nav_scraper/gen_nav_catalog.py  → 生成导航栏目录
- single_page_get/scraper.py      → 单页面爬取逻辑
- single_page_get/preprocess.js   → 浏览器端 HTML 预处理

用法：
    python build_data.py                  # 完整流程（含导航栏更新）
    python build_data.py --skip-nav       # 跳过导航栏更新，直接爬取
    python build_data.py --skip-existing  # 跳过已存在的文件（增量更新）
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
import time

# Windows 控制台默认 GBK 编码，无法输出 emoji，强制使用 utf-8
if sys.stdout is not None and sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr is not None and sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
NAV_MD_PATH = os.path.join(ROOT_DIR, "nav_scraper", "导航栏目录.md")
DATA_DIR = os.path.join(ROOT_DIR, "data")

# 将 single_page_get 加入搜索路径
sys.path.insert(0, os.path.join(ROOT_DIR, "single_page_get"))
sys.path.insert(0, os.path.join(ROOT_DIR, "nav_scraper"))


def parse_nav_catalog(md_path):
    """解析导航栏目录.md，返回所有页面条目列表"""
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    entries = []
    current_section_idx = 0
    current_section_name = ""
    current_entry_num = ""
    current_entry_name = ""
    for line in lines:
        line = line.rstrip("\n")
        # 匹配分区标题：## N 分区名
        section_match = re.match(r"^##\s+(\d+)\s+(.+)$", line)
        if section_match is not None:
            current_section_idx = int(section_match.group(1))
            current_section_name = section_match.group(2).strip()
            current_entry_num = ""
            current_entry_name = current_section_name
            continue
        # 匹配子条目标题：### / #### / ##### / ###### 编号 标题
        heading_match = re.match(r"^(#{3,6})\s+([\d.]+)\s+(.+)$", line)
        if heading_match is not None:
            current_entry_num = heading_match.group(2).strip()
            current_entry_name = heading_match.group(3).strip()
            continue
        # 匹配超过6级标题的缩进条目
        indent_match = re.match(r"^\s+([\d.]+)\s+(.+)$", line)
        if indent_match is not None:
            current_entry_num = indent_match.group(1).strip()
            current_entry_name = indent_match.group(2).strip()
            continue
        # 匹配链接行
        link_match = re.match(r"^链接：(https?://.+)$", line)
        if link_match is not None:
            url = link_match.group(1).strip()
            # 构建文件名（将 / 替换为 _，避免 Windows 路径问题）
            safe_name = current_entry_name.replace("/", "_")
            if current_entry_num == "":
                # 分区首页
                file_name = f"{current_section_name}.md"
            else:
                file_name = f"{current_entry_num} {safe_name}.md"
            # 构建文件夹名
            folder_name = f"{current_section_idx:02d}_{current_section_name}"
            entries.append(
                {
                    "section_idx": current_section_idx,
                    "section_name": current_section_name,
                    "folder_name": folder_name,
                    "entry_num": current_entry_num,
                    "entry_name": current_entry_name,
                    "file_name": file_name,
                    "url": url,
                }
            )
            continue
    return entries


def create_data_dirs(entries):
    """根据条目列表创建 data/ 目录结构"""
    os.makedirs(DATA_DIR, exist_ok=True)
    folder_names = sorted(set(e["folder_name"] for e in entries))
    for folder_name in folder_names:
        folder_path = os.path.join(DATA_DIR, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        print(f"  📁 {folder_name}/")
    return folder_names


def batch_scrape(entries, skip_existing=False):
    """批量爬取所有页面，复用浏览器实例"""
    # 延迟导入，避免在解析阶段就加载 Playwright
    from playwright.sync_api import sync_playwright
    from markdownify import markdownify as md_convert

    # 加载 JS 预处理脚本
    js_path = os.path.join(ROOT_DIR, "single_page_get", "preprocess.js")
    with open(js_path, "r", encoding="utf-8") as f:
        js_preprocess = f.read()
    # 导入 scraper 的后处理函数
    from scraper import scroll_page, post_process

    total = len(entries)
    success_count = 0
    skip_count = 0
    fail_count = 0
    fail_list = []
    print(f"\n{'='*60}")
    print(f"开始批量爬取：共 {total} 个页面")
    print(f"{'='*60}\n")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        for idx, entry in enumerate(entries, 1):
            output_path = os.path.join(
                DATA_DIR, entry["folder_name"], entry["file_name"]
            )
            url = entry["url"]
            progress = f"[{idx}/{total}]"
            # 跳过已存在的文件
            if skip_existing is True and os.path.exists(output_path) is True:
                print(f"{progress} ⏭ 跳过（已存在）: {entry['file_name']}")
                skip_count += 1
                continue
            print(f"{progress} 🔄 爬取: {entry['file_name']}")
            print(f"         URL: {url}")
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                images_loaded = scroll_page(page)
                page.wait_for_timeout(1000)
                raw_result = page.evaluate(js_preprocess)
                result = json.loads(raw_result)
                page_title = result.get("title", "").strip()
                html_content = result.get("html", "")
                if html_content == "":
                    print(f"         ⚠ 未找到内容区域，跳过")
                    fail_count += 1
                    fail_list.append({"entry": entry, "reason": "未找到内容区域"})
                    continue
                # 图片加载失败时，保存错误文档
                if images_loaded is False:
                    error_md = f"原文地址：{url}\n\n# {page_title}\n\n**错误：图片加载失败**\n\n经过 3 次重试后，页面中仍有图片未能加载。请检查网络连接后重新运行。\n"
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(error_md)
                    print(f"         ⚠ 图片加载失败，已保存错误文档")
                    fail_count += 1
                    fail_list.append({"entry": entry, "reason": "图片加载失败"})
                    continue
                # 转换为 Markdown
                markdown = md_convert(
                    html_content,
                    heading_style="ATX",
                    bullets="-",
                    strip=["script", "style", "button", "svg"],
                )
                markdown = post_process(markdown)
                # 去重标题
                if page_title:
                    stripped = markdown.lstrip("\n")
                    first_line = stripped.split("\n", 1)[0].strip()
                    if first_line == page_title:
                        rest = stripped.split("\n", 1)
                        markdown = rest[1].lstrip("\n") if len(rest) > 1 else ""
                # 添加来源链接和一级标题
                header = f"原文地址：{url}\n\n"
                if page_title:
                    header += f"# {page_title}\n\n"
                markdown = header + markdown
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(markdown)
                print(f"         ✅ 已保存 ({len(markdown)} 字符)")
                success_count += 1
            except Exception as ex:
                print(f"         ❌ 爬取失败: {ex}")
                fail_count += 1
                fail_list.append({"entry": entry, "reason": str(ex)})
            # 短暂等待，避免过于频繁的请求
            time.sleep(0.5)
        browser.close()
    return success_count, skip_count, fail_count, fail_list


def save_report(entries, success_count, skip_count, fail_count, fail_list):
    """保存构建报告"""
    report_path = os.path.join(ROOT_DIR, "build_report.json")
    report = {
        "total_entries": len(entries),
        "success": success_count,
        "skipped": skip_count,
        "failed": fail_count,
        "fail_details": [
            {
                "file": item["entry"]["file_name"],
                "url": item["entry"]["url"],
                "reason": item["reason"],
            }
            for item in fail_list
        ],
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n构建报告已保存: {report_path}")
    return report


def main():
    parser = argparse.ArgumentParser(description="扣子官方文档 - 数据构建集成脚本")
    parser.add_argument(
        "--skip-nav",
        action="store_true",
        help="跳过导航栏更新，使用现有的导航栏目录.md",
    )
    parser.add_argument(
        "--skip-existing", action="store_true", help="跳过已存在的文件（增量更新）"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="只解析目录，不实际爬取（用于检查）"
    )
    args = parser.parse_args()
    print("=" * 60)
    print("扣子官方文档 - 数据构建集成脚本")
    print("=" * 60)
    # ── 步骤1：生成导航栏目录 ──
    if args.skip_nav is False:
        print("\n📋 步骤1：生成最新的导航栏目录...")
        print("-" * 40)
        from gen_nav_catalog import main as gen_nav_main

        original_dir = os.getcwd()
        os.chdir(ROOT_DIR)
        gen_nav_main()
        os.chdir(original_dir)
    else:
        print("\n📋 步骤1：跳过导航栏更新（使用现有文件）")
    # ── 步骤2：解析导航栏目录 ──
    print("\n📖 步骤2：解析导航栏目录...")
    print("-" * 40)
    if os.path.exists(NAV_MD_PATH) is False:
        print(f"错误：找不到导航栏目录文件: {NAV_MD_PATH}")
        print("请先运行不带 --skip-nav 参数的完整流程")
        sys.exit(1)
    entries = parse_nav_catalog(NAV_MD_PATH)
    print(f"  共解析到 {len(entries)} 个页面条目")
    sections = {}
    for entry in entries:
        key = entry["folder_name"]
        if key not in sections:
            sections[key] = 0
        sections[key] += 1
    for folder_name, count in sorted(sections.items()):
        print(f"  📂 {folder_name}: {count} 个页面")
    # ── 步骤3：创建目录结构 ──
    print("\n📁 步骤3：创建 data/ 目录结构...")
    print("-" * 40)
    create_data_dirs(entries)
    # ── 步骤4：批量爬取 ──
    if args.dry_run is True:
        print("\n🔍 试运行模式：仅显示将要爬取的页面")
        print("-" * 40)
        for idx, entry in enumerate(entries, 1):
            print(f"  [{idx}] {entry['folder_name']}/{entry['file_name']}")
            print(f"       {entry['url']}")
        print(f"\n共 {len(entries)} 个页面待爬取")
        return
    print("\n🌐 步骤4：批量爬取页面...")
    print("-" * 40)
    success_count, skip_count, fail_count, fail_list = batch_scrape(
        entries, skip_existing=args.skip_existing
    )
    # ── 步骤5：输出报告 ──
    print("\n" + "=" * 60)
    print("📊 构建完成")
    print("=" * 60)
    print(f"  ✅ 成功: {success_count}")
    print(f"  ⏭ 跳过: {skip_count}")
    print(f"  ❌ 失败: {fail_count}")
    print(f"  📄 总计: {len(entries)}")
    if fail_count > 0:
        print("\n失败的页面：")
        for item in fail_list:
            print(f"  - {item['entry']['file_name']}: {item['reason']}")
    report = save_report(entries, success_count, skip_count, fail_count, fail_list)


if __name__ == "__main__":
    main()
