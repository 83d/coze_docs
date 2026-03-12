#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扣子文档单页面爬取工具
使用 Playwright + markdownify 将扣子文档页面转换为 Markdown 格式

功能：
1. 自动处理 JS 动态渲染
2. 转换自定义链接（at-doc）为标准 Markdown 链接
3. 转换 heading-h2/h3 等 class 为真实标题
4. 清理零宽字符、SVG 图标等无关元素
5. 移除页面导航（上一篇/下一篇）
6. 将"说明"文本块转换为引用块格式

使用方法：
    python scraper.py <URL> [输出文件路径]

示例：
    python scraper.py https://docs.coze.cn/cozespace/create-a-long-term-plan
    python scraper.py https://docs.coze.cn/cozespace/create-a-long-term-plan output.md
"""
import json
import os
import re
import sys
from playwright.sync_api import sync_playwright
from markdownify import markdownify as md

# 浏览器端 HTML 预处理脚本（从独立 .js 文件读取，方便在 VSCode 中高亮编辑）
_js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preprocess.js")
with open(_js_path, "r", encoding="utf-8") as _f:
    JS_PREPROCESS = _f.read()


def scroll_page(page):
    """滚动页面以触发图片懒加载，检查是否所有图片都加载成功，最多重试3次"""
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        # 逐个滚动到每张图片的位置，触发 IntersectionObserver 懒加载
        page.evaluate(
            """
            () => {
                return new Promise((resolve) => {
                    var imgs = document.querySelectorAll('.doc-content img[decoding="async"]');
                    var index = 0;
                    function scroll_next() {
                        if (index >= imgs.length) {
                            window.scrollTo(0, 0);
                            setTimeout(resolve, 500);
                            return;
                        }
                        imgs[index].scrollIntoView({behavior: 'instant', block: 'center'});
                        index += 1;
                        setTimeout(scroll_next, 300);
                    }
                    scroll_next();
                });
            }
        """
        )
        page.wait_for_timeout(1000)
        # 检查是否还有图片未加载（src 仍为 data: 占位符）
        unloaded_count = page.evaluate(
            """
            () => {
                var imgs = document.querySelectorAll('.doc-content img[decoding="async"]');
                var count = 0;
                for (var i = 0; i < imgs.length; i += 1) {
                    var src = imgs[i].getAttribute('src') || '';
                    if (src.startsWith('data:') === true) {
                        count += 1;
                    }
                }
                return count;
            }
        """
        )
        total_count = page.evaluate(
            """() => document.querySelectorAll('.doc-content img[decoding="async"]').length"""
        )
        if unloaded_count == 0:
            print(f"图片加载完成（共 {total_count} 张）")
            return True
        print(f"第 {attempt} 次滚动后仍有 {unloaded_count}/{total_count} 张图片未加载")
    print(f"警告：{max_retries} 次重试后仍有 {unloaded_count} 张图片未加载")
    return False


def post_process(markdown):
    """后处理 Markdown 文本"""
    # 清理零宽字符
    markdown = markdown.replace("\u200b", "")
    markdown = markdown.replace("​", "")
    # 清理多余空行
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    # 清理行尾空格
    lines = markdown.split("\n")
    lines = [line.rstrip() for line in lines]
    # 移除孤立的 `-` 列表项（图片占位符残留）
    result_lines = []
    for i, line in enumerate(lines):
        if line.strip() == "-":
            if i + 4 < len(lines):
                next_4 = [lines[i + 1], lines[i + 2], lines[i + 3], lines[i + 4]]
                if all(l.strip() == "" for l in next_4):
                    continue
        result_lines.append(line)
    lines = result_lines
    # 先清理空表头行（全是空格和竖线的行）
    result_lines = []
    for i, line in enumerate(lines):
        if re.match(r"^\|\s*\|\s*\|", line) and all(c in "| " for c in line):
            continue
        result_lines.append(line)
    lines = result_lines
    # 再修复表格格式：如果分隔符行在表头之前，交换它们的位置
    result_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 检测分隔符行（全是 | 和 --- 组成）
        if re.match(r"^\|\s*---", line):
            # 检查下一行是否是表头（包含文字内容）
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.startswith("|") and not re.match(r"^\|\s*---", next_line):
                    # 交换分隔符行和表头行
                    result_lines.append(next_line)
                    result_lines.append(line)
                    i += 2
                    continue
        result_lines.append(line)
        i += 1
    lines = result_lines
    # 移除末尾的"上一篇""下一篇"导航
    final_lines = []
    for i, line in enumerate(result_lines):
        if line.strip() == "上一篇" or line.strip() == "下一篇":
            remaining = "\n".join(result_lines[i:]).strip()
            if "上一篇" in remaining and "下一篇" in remaining:
                break
        final_lines.append(line)
    # 最终清理多余空行
    text = "\n".join(final_lines).strip() + "\n"
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text


def scrape_page(url, output_path=None):
    """爬取单个页面并转换为 Markdown"""
    print(f"目标页面: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        images_loaded = scroll_page(page)
        page.wait_for_timeout(1000)
        raw_result = page.evaluate(JS_PREPROCESS)
        browser.close()
    result = json.loads(raw_result)
    page_title = result.get("title", "").strip()
    html_content = result.get("html", "")
    if html_content == "":
        print("未找到内容区域")
        return None
    # 用页面标题作为文件名
    if output_path is None:
        if page_title:
            output_path = f"{page_title}.md"
        else:
            slug = url.rstrip("/").split("/")[-1]
            output_path = f"{slug}.md"
    # 图片加载失败时，输出错误文档
    if images_loaded is False:
        error_md = f"原文地址：{url}\n\n# {page_title}\n\n**错误：图片加载失败**\n\n经过 3 次重试后，页面中仍有图片未能加载。请检查网络连接后重新运行。\n"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(error_md)
        print(f"已保存错误文档到 {output_path}")
        return None
    print(f"页面标题: {page_title}")
    print(f"预处理后 HTML 长度: {len(html_content)} 字符")
    markdown = md(
        html_content,
        heading_style="ATX",
        bullets="-",
        strip=["script", "style", "button", "svg"],
    )
    markdown = post_process(markdown)
    # 如果正文开头就是标题文本（与 page_title 重复），去掉它
    if page_title:
        stripped = markdown.lstrip("\n")
        first_line = stripped.split("\n", 1)[0].strip()
        if first_line == page_title:
            rest = stripped.split("\n", 1)
            markdown = rest[1].lstrip("\n") if len(rest) > 1 else ""
    # 在文档顶部添加来源链接和一级标题
    header = f"原文地址：{url}\n\n"
    if page_title:
        header += f"# {page_title}\n\n"
    markdown = header + markdown
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"已保存到 {output_path}")
    print(f"Markdown 长度: {len(markdown)} 字符")
    return markdown


def main():
    if len(sys.argv) < 2:
        print("用法: python scraper.py <URL> [输出文件路径]")
        print(
            "示例: python scraper.py https://docs.coze.cn/cozespace/create-a-long-term-plan"
        )
        sys.exit(1)
    url = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    scrape_page(url, output_path)


if __name__ == "__main__":
    scrape_page("https://docs.coze.cn/cozespace/create-a-long-term-plan")
