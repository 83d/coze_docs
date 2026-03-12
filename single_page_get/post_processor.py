#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 markdownify 输出的 Markdown 格式问题
1. 移除孤立的 `-` 列表项（图片占位符残留）
2. 修复有序列表格式
3. 清理空表头
"""
import re
import sys


def remove_orphan_dashes(text):
    """移除孤立的 `-` 列表项（图片占位符残留）"""
    lines = text.split("\n")
    result = []
    for i, line in enumerate(lines):
        # 孤立的 `-` 后面跟着多个空行
        if line.strip() == "-":
            # 检查后面是否有4个空行
            if i + 4 < len(lines):
                next_4 = [lines[i + 1], lines[i + 2], lines[i + 3], lines[i + 4]]
                if all(l.strip() == "" for l in next_4):
                    # 跳过这个孤立的 `-` 和后面的空行
                    continue
        result.append(line)
    return "\n".join(result)


def fix_ordered_lists(text):
    """修复有序列表格式 — 将独立的编号行与内容合并"""
    lines = text.split("\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 检测独立的编号行（1. 2. 3. 或 a. b. c.）
        match = re.match(r"^(\d+\.|[a-z]\.)$", line.strip())
        if match:
            # 查找后续的内容行
            i += 1
            # 跳过空行
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            # 获取内容
            if i < len(lines):
                content = lines[i].strip()
                # 合并为标准列表格式
                result.append(f"{match.group(1)} {content}")
                i += 1
                continue
        result.append(line)
        i += 1
    return "\n".join(result)


def clean_empty_table_headers(text):
    """清理空表头行"""
    lines = text.split("\n")
    result = []
    for i, line in enumerate(lines):
        # 检测空表头（只有分隔符的行）
        if re.match(r"^\|\s*\|\s*\|\s*\|\s*\|\s*\|\s*\|\s*\|$", line):
            # 检查下一行是否是分隔符行
            if i + 1 < len(lines) and re.match(r"^\|\s*---", lines[i + 1]):
                # 跳过这个空表头
                continue
        result.append(line)
    return "\n".join(result)


def clean_multiple_blank_lines(text):
    """清理多余的空行（超过2个连续空行压缩为2个）"""
    return re.sub(r"\n{4,}", "\n\n\n", text)


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "test_markdownify_v2_output.md"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "test_markdownify_v3_output.md"
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()
    print(f"原始文件: {len(text)} 字符")
    text = remove_orphan_dashes(text)
    print(f"移除孤立 - 后: {len(text)} 字符")
    text = fix_ordered_lists(text)
    print(f"修复有序列表后: {len(text)} 字符")
    text = clean_empty_table_headers(text)
    print(f"清理空表头后: {len(text)} 字符")
    text = clean_multiple_blank_lines(text)
    print(f"清理多余空行后: {len(text)} 字符")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\n已保存到 {output_file}")


if __name__ == "__main__":
    main()
