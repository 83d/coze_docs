# 扣子官方文档 Markdown 转换项目

将 [扣子官方文档](https://docs.coze.cn) 全站内容自动爬取并转换为 Markdown 格式。

> ⚠️ **关于 `data/` 目录中的数据**
>
> 本仓库 `data/` 目录下的 **882 个 Markdown 文件**是 **2026 年 3 月 12 日**爬取的快照数据。
> 扣子官方文档会持续更新，如果你需要获取最新版本的文档内容，请按照下方「快速开始」章节的步骤，自行运行 Python 爬虫程序重新爬取。
>
> ```bash
> # 1. 安装依赖
> pip install playwright markdownify beautifulsoup4
> python -m playwright install chromium
>
> # 2. 一键重新爬取全站最新数据（会覆盖 data/ 目录下的旧文件）
> python build_data.py
>
> # 3. 或者只更新新增的页面（保留已有文件，只爬取新增的）
> python build_data.py --skip-existing
> ```

## 项目结构

```
.
├── build_data.py                  # ⭐ 一键构建脚本（集成入口）
├── nav_scraper/                   # 导航栏爬取模块
│   ├── gen_nav_catalog.py         #   生成导航栏目录
│   └── 导航栏目录.md               #   输出：完整的文档目录树（2919 行）
├── single_page_get/               # 单页面爬取模块
│   ├── scraper.py                 #   核心爬虫：Playwright + markdownify
│   ├── preprocess.js              #   浏览器端 HTML 预处理
│   └── post_processor.py          #   Markdown 后处理工具
├── data/                          # 输出：转换后的 Markdown 文档（882 个文件）
│   ├── 01_扣子/                   #   25 个文件
│   ├── 02_扣子编程/               #   432 个文件
│   ├── 03_开发指南/               #   32 个文件
│   ├── 04_API 和 SDK/             #   192 个文件
│   ├── 05_实践教程/               #   63 个文件
│   ├── 06_扣子罗盘/               #   79 个文件
│   ├── 07_客户案例/               #   30 个文件
│   └── 08_定价与购买/             #   29 个文件
└── .gitignore
```

## 快速开始

### 环境准备

```bash
pip install playwright markdownify beautifulsoup4
python -m playwright install chromium
```

### 一键构建全部数据

```bash
python build_data.py
```

这个命令会自动完成以下全部步骤：

1. **爬取导航栏** -- 启动浏览器访问 docs.coze.cn，展开所有导航项，生成导航栏目录.md
2. **解析目录结构** -- 从导航栏目录中提取所有页面条目（编号、名称、URL）
3. **创建文件夹** -- 按 8 大分区创建 data/ 目录结构
4. **批量爬取** -- 逐个爬取所有页面，复用浏览器实例，转换为 Markdown
5. **输出报告** -- 生成 build_report.json 记录成功/失败/跳过的详情

### 命令行参数

```bash
# 跳过导航栏更新（使用现有的导航栏目录.md）
python build_data.py --skip-nav

# 增量更新：跳过已存在的文件
python build_data.py --skip-existing

# 试运行：只解析目录，不实际爬取（用于检查）
python build_data.py --dry-run

# 组合使用
python build_data.py --skip-nav --skip-existing
```

## 数据构建流程详解

整个流程由 build_data.py 集成，依赖两个核心模块：

```
                ┌──────────────────────┐
                │    build_data.py     │  集成入口
                │  （一键构建脚本）      │
                └──────┬───────┬───────┘
                       │       │
          ┌────────────┘       └────────────┐
          ▼                                 ▼
┌──────────────────┐              ┌──────────────────┐
│  nav_scraper/    │              │ single_page_get/ │
│ gen_nav_catalog  │              │    scraper.py    │
│ （导航栏爬取）    │              │  （页面爬取）     │
└────────┬─────────┘              └────────┬─────────┘
         │                                 │
         ▼                                 ▼
  导航栏目录.md                        data/*.md
  （882 个页面条目）                （Markdown 文档）
```

### 步骤 1：导航栏爬取（nav_scraper）

gen_nav_catalog.py 使用 Playwright 访问 docs.coze.cn 的 8 个分区首页，
自动展开所有折叠的导航项，用 BeautifulSoup 解析 DOM 嵌套关系确定层级，
输出完整的目录树。

输出文件：nav_scraper/导航栏目录.md

目录格式示例：
```markdown
## 1 扣子
链接：https://docs.coze.cn/cozespace

### 1.1 了解扣子
链接：https://docs.coze.cn/cozespace/overview

### 1.4 活动与公告

#### 1.4.1 扣子活动合集
链接：https://docs.coze.cn/cozespace/space_event_collection
```

### 步骤 2：单页面爬取（single_page_get）

scraper.py 对每个页面执行：

1. 加载页面 -- Playwright 打开 URL，等待 JS 动态渲染完成
2. 懒加载图片 -- 逐个滚动到每张图片位置，触发 IntersectionObserver
3. HTML 预处理（preprocess.js）：
   - 处理 picture 标签，选择最佳图片源
   - CSS 内联加粗/斜体转语义化 strong/em 标签
   - heading-h2/h3 class 转真实 h2/h3 标签
   - at-doc 自定义链接转标准 a 标签
   - 高亮提示区块转 GFM Alerts 语法 blockquote
   - 有序列表非标准结构转标准 ol/li 结构
4. Markdown 转换 -- markdownify 将预处理后的 HTML 转为 Markdown
5. 后处理 -- 清理零宽字符、修复表格格式、移除导航残留

### 步骤 3：批量构建

build_data.py 解析导航栏目录，复用浏览器实例批量爬取所有页面：

- 文件命名：`编号 标题.md`（如 `1.5.2 制作技能.md`）
- 分区首页：`分区名.md`（如 `扣子.md`）
- 目录结构：`data/0N_分区名/`（如 `data/01_扣子/`）

## 8 大分区

| 分区 | 文件夹 | 说明 |
|------|--------|------|
| 扣子 | 01_扣子 | 扣子空间功能指南 |
| 扣子编程 | 02_扣子编程 | 低代码/AI编程开发文档 |
| 开发指南 | 03_开发指南 | 音视频、渠道入驻等 |
| API 和 SDK | 04_API 和 SDK | REST API / SDK 参考 |
| 实践教程 | 05_实践教程 | 场景化教程与案例 |
| 扣子罗盘 | 06_扣子罗盘 | 提示词、评测、观测 |
| 客户案例 | 07_客户案例 | 企业客户使用案例 |
| 定价与购买 | 08_定价与购买 | 计费规则与套餐 |

## 单独使用子模块

### 只更新导航栏目录

```bash
python nav_scraper/gen_nav_catalog.py
```

### 只爬取单个页面

```bash
python single_page_get/scraper.py https://docs.coze.cn/cozespace/overview
python single_page_get/scraper.py https://docs.coze.cn/cozespace/overview output.md
```

## 依赖

```bash
pip install playwright markdownify beautifulsoup4
python -m playwright install chromium
```

## 注意事项

- 首次运行需要安装 Chromium 浏览器（playwright install chromium）
- 批量爬取 882 个页面需要较长时间，建议使用 --skip-existing 进行增量更新
- 爬取过程中如果某个页面失败，会记录在 build_report.json 中，可以后续单独重试
- 图片使用原始 URL（CDN 链接），不做本地下载
