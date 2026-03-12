/**
 * 浏览器端 HTML 预处理脚本
 * 在 markdownify 转换之前，修复扣子文档中的非标准 HTML 结构
 * 由 scraper.py 通过 Playwright page.evaluate() 调用
 */
() => {
    // ── 子函数定义 ──

    /**
     * 处理高亮提示区块（.highlight-block-v2）→ 转换为 GFM Alerts 语法的 blockquote
     * DOM 结构：.highlight-block-v2 > .highlight-block-present-title（标题） + .highlight-block-body（内容）
     * 中文标题自动映射为 GFM Alert 类型：说明→NOTE, 注意→WARNING, 提示→TIP, 重要→IMPORTANT, 警告→CAUTION
     */
    function convert_highlight_blocks(container) {
        var highlight_blocks = container.querySelectorAll('.highlight-block-v2');
        for (var i = 0; i < highlight_blocks.length; i += 1) {
            var hb = highlight_blocks[i];
            var title_el = hb.querySelector('.highlight-block-present-title');
            var body_el = hb.querySelector('.highlight-block-body');
            if (body_el === null) { continue; }
            var content_html = '';
            if (title_el !== null) {
                var title_text = title_el.textContent.replace(/\u200b/g, '').trim();
                if (title_text.length > 0) {
                    content_html = '<p><strong>' + title_text + '</strong></p>';
                }
            }
            content_html = content_html + body_el.innerHTML;
            var bq = document.createElement('blockquote');
            bq.innerHTML = '<p>[!NOTE]</p>' + content_html;
            hb.parentNode.replaceChild(bq, hb);
        }
    }

    // ── 主流程 ──

    var main = document.querySelector('.doc-content');
    if (main === null) { return JSON.stringify({title: '', html: ''}); }

    // 0.5. 处理 <picture> 标签：按照浏览器规则选择最佳图片源
    var pictures = main.querySelectorAll('picture');
    var supported_types = ['image/webp', 'image/avif', 'image/jpeg', 'image/png', 'image/gif'];
    for (var pi = 0; pi < pictures.length; pi += 1) {
        var pic = pictures[pi];
        var img_el = pic.querySelector('img');
        if (img_el === null) { continue; }
        var best_src = '';
        var sources = pic.querySelectorAll('source');
        for (var si = 0; si < sources.length; si += 1) {
            var source = sources[si];
            var type_attr = source.getAttribute('type') || '';
            if (type_attr.length > 0) {
                var is_supported = false;
                for (var ti = 0; ti < supported_types.length; ti += 1) {
                    if (type_attr === supported_types[ti]) {
                        is_supported = true;
                        break;
                    }
                }
                if (is_supported === false) { continue; }
            }
            var srcset = source.getAttribute('srcset') || '';
            if (srcset.length > 0) {
                var candidates = srcset.split(',');
                var best_candidate = '';
                var best_density = 0;
                for (var ci = 0; ci < candidates.length; ci += 1) {
                    var parts = candidates[ci].trim().split(' ');
                    var url = parts[0];
                    var density = 1;
                    if (parts.length > 1) {
                        var descriptor = parts[1];
                        if (descriptor.indexOf('x') !== -1) {
                            density = parseFloat(descriptor.replace('x', '')) || 1;
                        }
                    }
                    if (density > best_density) {
                        best_density = density;
                        best_candidate = url;
                    }
                }
                if (best_candidate.length > 0) {
                    best_src = best_candidate;
                    break;
                }
            }
            var src_attr = source.getAttribute('src') || '';
            if (src_attr.length > 0) {
                best_src = src_attr;
                break;
            }
        }
        if (best_src.length === 0) {
            best_src = img_el.getAttribute('src') || '';
        }
        if (best_src.length === 0) { continue; }
        var width_attr = img_el.getAttribute('width') || '';
        var height_attr = img_el.getAttribute('height') || '';
        var alt_text = img_el.getAttribute('alt') || '';
        var html_text = '<img src="' + best_src + '"';
        if (alt_text.length > 0) {
            html_text = html_text + ' alt="' + alt_text + '"';
        }
        if (width_attr.length > 0 && height_attr.length > 0) {
            html_text = html_text + ' width="' + width_attr + '"';
        } else if (width_attr.length > 0) {
            html_text = html_text + ' width="' + width_attr + '"';
        } else if (height_attr.length > 0) {
            html_text = html_text + ' height="' + height_attr + '"';
        }
        html_text = html_text + '>';
        var span = document.createElement('span');
        span.className = 'md-image';
        span.textContent = html_text;
        pic.parentNode.replaceChild(span, pic);
    }

    // 0. 提取页面标题（div.title），转为 h1 标签插入到内容顶部
    var page_title = '';
    var title_el = document.querySelector('.docPageHeader .title, #doc-title .title');
    if (title_el !== null) {
        page_title = title_el.textContent.replace(/\u200b/g, '').trim();
    }

    // 1. 把 CSS 内联样式的加粗/斜体转成语义化标签（markdownify 不解析 style 属性）
    // 一个元素可能同时有加粗和斜体，所以一次性检查两种样式，用包裹而非替换
    var styled_els = main.querySelectorAll('[style*="font-weight"], [style*="font-style"]');
    for (var si = 0; si < styled_els.length; si += 1) {
        var sel = styled_els[si];
        var st = sel.getAttribute('style') || '';
        var is_bold = st.indexOf('font-weight: bold') !== -1 || st.indexOf('font-weight:bold') !== -1;
        var is_italic = st.indexOf('font-style: italic') !== -1 || st.indexOf('font-style:italic') !== -1;
        if (is_bold === false && is_italic === false) { continue; }
        // 用包裹方式：在元素内部套上 <strong> 和/或 <em>
        var inner_html = sel.innerHTML;
        if (is_bold === true) {
            inner_html = '<strong>' + inner_html + '</strong>';
        }
        if (is_italic === true) {
            inner_html = '<em>' + inner_html + '</em>';
        }
        sel.innerHTML = inner_html;
    }

    // 2. 把 heading-h2/h3/h4 class 的 div 转成真正的 h 标签
    var heading_classes = ['heading-h1','heading-h2','heading-h3','heading-h4','heading-h5','heading-h6'];
    for (var hi = 0; hi < heading_classes.length; hi += 1) {
        var cls = heading_classes[hi];
        var level = cls.replace('heading-h', '');
        var els = main.querySelectorAll('.' + cls);
        for (var ei = 0; ei < els.length; ei += 1) {
            var el = els[ei];
            var text = el.textContent.replace(/\u200b/g, '').replace(/\s+/g, ' ').trim();
            if (text.length === 0) { continue; }
            var h = document.createElement('h' + level);
            h.textContent = text;
            el.parentNode.replaceChild(h, el);
        }
    }

    // 3. 把 at-doc 自定义链接转成标准 <a> 标签
    // HTML 结构：<span data-leaf><span data-rect-container><span data-zero-space>​</span><span data-fake-text><span class="at-doc is-active" title="/path">...<span>链接文字</span></span></span></span></span>
    // 需要把整个 data-leaf 层的 span 替换为 <a>
    var at_docs = main.querySelectorAll('.at-doc.is-active');
    for (var ai = 0; ai < at_docs.length; ai += 1) {
        var at = at_docs[ai];
        var href = at.getAttribute('title') || '';
        var link_text = '';
        // 取 at-doc 内最后一个纯文本 span（跳过 svg 图标）
        var spans = at.querySelectorAll('span');
        for (var si = 0; si < spans.length; si += 1) {
            var t = spans[si].textContent.replace(/\u200b/g, '').trim();
            if (t.length > 0 && spans[si].querySelector('svg') === null) {
                link_text = t;
            }
        }
        if (link_text.length === 0) {
            link_text = at.textContent.replace(/\u200b/g, '').trim();
        }
        if (href.length === 0 || link_text.length === 0) { continue; }
        // 补全相对路径
        if (href.startsWith('/')) {
            href = 'https://docs.coze.cn' + href;
        }
        var a = document.createElement('a');
        a.href = href;
        a.textContent = link_text;
        // 向上查找到 data-leaf 层级的 span 进行替换
        // at-doc -> data-fake-text -> data-rect-container -> data-leaf
        var container = at;
        while (container.parentNode && container.parentNode !== main) {
            var parent = container.parentNode;
            if (parent.getAttribute('data-fake-text') !== null ||
                parent.getAttribute('data-rect-container') !== null ||
                parent.getAttribute('data-leaf') !== null) {
                container = parent;
            } else {
                break;
            }
        }
        container.parentNode.replaceChild(a, container);
    }

    // 4. 处理高亮提示区块（.highlight-block-v2）→ 转换为 GFM Alerts 语法的 blockquote
    convert_highlight_blocks(main);

    // 5. 移除 aria-hidden 的占位 img（懒加载的尺寸撑开器），图片本身交给 markdownify 处理
    var hidden_imgs = main.querySelectorAll('img[aria-hidden="true"]');
    for (var hi2 = 0; hi2 < hidden_imgs.length; hi2 += 1) {
        hidden_imgs[hi2].remove();
    }

    // 6. 处理有序列表：扣子文档的有序列表是非标准结构
    // 每个列表项是独立的 <ol>，编号在 button.list-button 里，内容在 div.ordered-list-content 里
    // 移除 button，把 div 转成 <li>，让 markdownify 按标准 <ol><li> 处理
    var list_buttons = main.querySelectorAll('button.list-button');
    for (var lbi = 0; lbi < list_buttons.length; lbi += 1) {
        var lb = list_buttons[lbi];
        var ol = lb.parentElement;
        var content_div = ol.querySelector('.ordered-list-content');
        if (content_div === null) { continue; }
        lb.remove();
        var li = document.createElement('li');
        li.innerHTML = content_div.innerHTML;
        content_div.parentNode.replaceChild(li, content_div);
    }

    // 7. 移除 svg、button、无关元素
    var removes = main.querySelectorAll('svg, button, [class*="icon-link"], [class*="copy-btn"]');
    for (var ri = 0; ri < removes.length; ri += 1) {
        removes[ri].remove();
    }

    // 8. 清理零宽字符
    // 这个在 JS 端不好全局替换 innerHTML，留给 Python 端处理
    return JSON.stringify({title: page_title, html: main.innerHTML});
}
