"""
从 docs.coze.cn 获取所有分类的导航栏 HTML
用 BeautifulSoup 解析 DOM 嵌套关系确定层级
保存为纯文本格式的 导航栏目录.md
"""

import json
import os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

SECTIONS = [
    ("扣子", "/cozespace"),
    ("扣子编程", "/guides"),
    ("开发指南", "/dev_how_to_guides"),
    ("API 和 SDK", "/developer_guides"),
    ("实践教程", "/tutorial"),
    ("扣子罗盘", "/cozeloop"),
    ("客户案例", "/customers"),
    ("定价与购买", "/coze_pro"),
]
BASE = "https://docs.coze.cn"


def fmt(num, total):
    if total > 9:
        return f"{num:02d}"
    return str(num)


def find_nav_js(base_path):
    """返回 JS 代码片段，根据 base_path 找到对应的导航容器"""
    return f"""
        var navs = document.querySelectorAll('.playground-sub-menu-APnOTK');
        var nav = null;
        for (var i = 0; i < navs.length; i += 1) {{
            var first_link = navs[i].querySelector('a[href]');
            if (first_link !== null) {{
                var href = first_link.getAttribute('href') || '';
                if (href === '{base_path}') {{
                    nav = navs[i];
                    break;
                }}
            }}
        }}
    """


def expand_all(page, base_path):
    for _ in range(30):
        count = page.evaluate(
            """(basePath) => {
            var navs = document.querySelectorAll('.playground-sub-menu-APnOTK');
            var nav = null;
            for (var i = 0; i < navs.length; i += 1) {
                var first_link = navs[i].querySelector('a[href]');
                if (first_link !== null) {
                    var href = first_link.getAttribute('href') || '';
                    if (href === basePath) {
                        nav = navs[i];
                        break;
                    }
                }
            }
            if (nav === null) return 0;
            var svgs = nav.querySelectorAll('svg');
            var clicked = 0;
            for (var i = 0; i < svgs.length; i += 1) {
                var cls = svgs[i].getAttribute('class') || '';
                if (cls.indexOf('arrow_down') >= 0) {
                    var target = svgs[i].closest('a') || svgs[i].closest('div');
                    if (target !== null) {
                        target.click();
                        clicked += 1;
                    }
                }
            }
            return clicked;
        }""",
            base_path,
        )
        if count == 0:
            break
        page.wait_for_timeout(800)


def get_nav_html(page, base_path):
    return page.evaluate(
        """(basePath) => {
        var navs = document.querySelectorAll('.playground-sub-menu-APnOTK');
        for (var i = 0; i < navs.length; i += 1) {
            var first_link = navs[i].querySelector('a[href]');
            if (first_link !== null) {
                var href = first_link.getAttribute('href') || '';
                if (href === basePath) {
                    return navs[i].outerHTML;
                }
            }
        }
        return '';
    }""",
        base_path,
    )


def get_text(el):
    for span in el.find_all("span"):
        if span.find("span") is not None:
            continue
        t = span.get_text(strip=True).replace("\u200b", "")
        if t != "":
            return t
    return el.get_text(strip=True).replace("\u200b", "")


def parse(container, base_path):
    """递归解析容器中的链接和分组"""
    items = []
    if container is None:
        return items
    for child in container.children:
        if not hasattr(child, "name") or child.name is None:
            continue
        cls_str = " ".join(child.get("class", []))
        if child.name == "a":
            href = child.get("href", "")
            if href == "" or href == base_path:
                continue
            if href.startswith(base_path + "/") == False:
                continue
            text = get_text(child)
            if text != "":
                items.append({"text": text, "href": href, "children": []})
        elif child.name == "div" and "semi-collapse-item" in cls_str:
            header = child.find(
                "div", class_=lambda c: c and "semi-collapse-header" in c
            )
            if header is None:
                continue
            title = get_text(header)
            if title == "":
                continue
            cw = child.find(
                "div", class_=lambda c: c and "semi-collapse-content-wrapper" in c
            )
            sub = parse(cw, base_path) if cw is not None else []
            items.append({"text": title, "href": "", "children": sub})
        elif child.name == "div":
            sub = parse(child, base_path)
            items.extend(sub)
    return items


def tree_to_lines(nodes, prefix, heading_level):
    """递归生成 Markdown 标题层级目录"""
    lines = []
    total = len(nodes)
    for idx, node in enumerate(nodes, 1):
        num_str = fmt(idx, total)
        cur = f"{prefix}{num_str}"
        # Markdown 标题最多 6 级，超过的用缩进代替
        if heading_level <= 6:
            hashes = "#" * heading_level
            lines.append(f"{hashes} {cur} {node['text']}")
        else:
            indent = "  " * (heading_level - 6)
            lines.append(f"{indent}{cur} {node['text']}")
        if node["href"] != "":
            url = BASE + node["href"]
            lines.append(f"链接：{url}")
        lines.append("")
        if len(node["children"]) > 0:
            lines.extend(tree_to_lines(node["children"], cur + ".", heading_level + 1))
    return lines


def main():
    os.makedirs("cache", exist_ok=True)
    print("正在读取导航栏完整层级结构...\n", flush=True)
    all_data = {}
    md_lines = ["# 扣子官方文档 - 导航栏目录\n"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        for sec_idx, (sec_name, sec_url) in enumerate(SECTIONS, 1):
            print(f"[{sec_idx}/{len(SECTIONS)}] {sec_name}...", flush=True)
            page.goto(f"{BASE}{sec_url}", wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            expand_all(page, sec_url)
            page.wait_for_timeout(2000)
            html = get_nav_html(page, sec_url)
            soup = BeautifulSoup(html, "html.parser")
            wrapper = soup.find(
                "div", class_=lambda c: c and "semi-collapsible-wrapper" in c
            )
            if wrapper is None:
                print(f"  ✗ 找不到 semi-collapsible-wrapper", flush=True)
                continue
            collapse = wrapper.find(
                "div",
                class_=lambda c: c
                and "semi-collapse" in c
                and "item" not in c
                and "header" not in c
                and "content" not in c
                and "wrapper" not in c,
            )
            if collapse is None:
                print(f"  ✗ 找不到 semi-collapse", flush=True)
                continue
            tree = parse(collapse, sec_url)
            all_data[sec_name] = tree
            sec_num = fmt(sec_idx, len(SECTIONS))
            url = f"{BASE}{sec_url}"
            md_lines.append(f"\n## {sec_num} {sec_name}")
            md_lines.append(f"链接：{url}\n")
            sub_lines = tree_to_lines(tree, sec_num + ".", 3)
            md_lines.extend(sub_lines)

            def count_nodes(nodes):
                c = len(nodes)
                for n in nodes:
                    c += count_nodes(n.get("children", []))
                return c

            total = count_nodes(tree)
            print(f"  {len(tree)} 个顶级项, 总计 {total} 个", flush=True)
        browser.close()
    # 保存 JSON 到 cache 目录
    with open("cache/nav_tree_full.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    # 保存导航栏目录到 nav_scraper 目录（固定位置，供 build_data.py 使用）
    md_text = "\n".join(md_lines) + "\n"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    nav_md_path = os.path.join(script_dir, "导航栏目录.md")
    with open(nav_md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    print(f"\n已保存: {nav_md_path} ({len(md_lines)} 行)", flush=True)
    print(f"已保存: cache/nav_tree_full.json", flush=True)


if __name__ == "__main__":
    main()
