// split from emails.js → render.js
        function paintEmailListColdFetchPrompt(folder = currentFolder) {
            const listEl = document.getElementById('emailList');
            if (!listEl) return;
            listEl.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon" aria-hidden="true"></span>
                    <p class="ui-empty-title">${getEmailListColdFetchPrompt(folder)}</p>
                    <button type="button" class="btn btn-primary btn-sm" onclick="refreshEmails()">${translateAppTextLocal('获取邮件')}</button>
                </div>
            `;
        }

        // Expose for switchFolder (main.js) so language re-paint shares the same chrome.
        window.getEmailListColdFetchPrompt = getEmailListColdFetchPrompt;
        window.paintEmailListColdFetchPrompt = paintEmailListColdFetchPrompt;

        function renderEmailList(emails, options = {}) {
            const container = document.getElementById('emailList');
            const actionBar = document.getElementById('emailBatchActionBar');

            if (emails.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <span class="empty-icon" aria-hidden="true"></span>
                        <p class="ui-empty-title">${getEmailListEmptyMessage()}</p>
                        <button type="button" class="btn btn-primary btn-sm" onclick="refreshEmails()">${translateAppTextLocal('获取邮件')}</button>
                    </div>
                `;
                selectedEmailIds.clear();
                updateEmailBatchActionBar();
                if (options.scrollToTop !== false) container.scrollTop = 0;
                return;
            }

            const clickHandler = isTempEmailGroup ? 'getTempEmailDetail' : 'selectEmail';
            // Bug #24 修复：用 currentEmailDetail.id 保留 active 状态
            const currentActiveId = currentEmailDetail ? currentEmailDetail.id : null;

            container.innerHTML = emails.map((email, index) => {
                const isChecked = selectedEmailIds.has(email.id);
                const isActive = currentActiveId && email.id === currentActiveId;
                const initial = (email.from || '?')[0].toUpperCase();
                return `
                <div class="email-item ${email.is_read === false ? 'unread' : ''} ${isActive ? 'active' : ''}"
                     onclick="${clickHandler}('${email.id}', ${index})">
                    <div class="email-checkbox-wrapper" onclick="event.stopPropagation(); toggleEmailSelection('${email.id}')">
                        <input type="checkbox" class="email-checkbox" ${isChecked ? 'checked' : ''} style="pointer-events: none;">
                    </div>
                    <div class="email-avatar">${initial}</div>
                    <div class="email-meta">
                        <div class="email-from">${escapeHtml(email.from)}</div>
                        <div class="email-subject">${escapeHtml(email.subject || '无主题')}</div>
                        <div class="email-preview">${escapeHtml(email.body_preview || '')}</div>
                    </div>
                    <div class="email-time">${formatDate(email.date)}</div>
                </div>
            `}).join('');

            // Issue #52: 加载/刷新后自动回到列表顶部，避免滚动位置乱跑
            if (options.scrollToTop !== false) container.scrollTop = 0;

            updateEmailBatchActionBar();
        }

        function renderEmailDetail(email, options = {}) {
            const refs = getEmailDetailRefs(options);
            const container = refs.container;
            if (!container) {
                return;
            }
            const rawBody = typeof email.body === 'string' ? email.body : '';
            const iframeId = refs.iframeId;

            const isHtml = email.body_type === 'html' ||
                (rawBody && (rawBody.includes('<html') || rawBody.includes('<div') || rawBody.includes('<p>')));

            const bodyContent = isHtml
                ? `<iframe id="${iframeId}" class="email-body-frame" sandbox="allow-same-origin" onload="adjustIframeHeight(this)"></iframe>`
                : `<div class="email-body-text">${escapeHtml(rawBody)}</div>`;

            container.innerHTML = `
                <div class="email-detail-header">
                    <div class="email-detail-subject">${escapeHtml(email.subject || '无主题')}</div>
                    <div class="email-detail-meta">
                        <div class="email-detail-meta-row">
                            <span class="email-detail-meta-label">发件人</span>
                            <span class="email-detail-meta-value">${escapeHtml(email.from)}</span>
                        </div>
                        <div class="email-detail-meta-row">
                            <span class="email-detail-meta-label">收件人</span>
                            <span class="email-detail-meta-value">${escapeHtml(email.to || '-')}</span>
                        </div>
                        ${email.cc ? `
                        <div class="email-detail-meta-row">
                            <span class="email-detail-meta-label">抄送</span>
                            <span class="email-detail-meta-value">${escapeHtml(email.cc)}</span>
                        </div>
                        ` : ''}
                        <div class="email-detail-meta-row">
                            <span class="email-detail-meta-label">时间</span>
                            <span class="email-detail-meta-value">${formatDate(email.date)}</span>
                        </div>
                    </div>
                </div>
                <div class="email-detail-body">
                    ${bodyContent}
                </div>
            `;

            // 如果是 HTML 内容，设置 iframe 内容
            if (isHtml) {
                const iframe = container.querySelector(`#${iframeId}`) || container.querySelector('.email-body-frame');
                if (iframe) {
                    const renderableBody = rewriteEmailInlineImages(rawBody, email);
                    let sanitizedBody;
                    if (isTrustedMode) {
                        sanitizedBody = renderableBody; // 信任模式：不过滤
                    } else if (typeof DOMPurify !== 'undefined') {
                        // 使用 DOMPurify 净化 HTML 内容，防止 XSS 攻击
                        sanitizedBody = DOMPurify.sanitize(renderableBody, {
                            ALLOWED_TAGS: ['a', 'b', 'i', 'u', 'strong', 'em', 'p', 'br', 'div', 'span', 'img', 'table', 'tr', 'td', 'th', 'thead', 'tbody', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre', 'code', 'style'],
                            ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'style', 'class', 'width', 'height', 'align', 'border', 'cellpadding', 'cellspacing'],
                            ALLOW_DATA_ATTR: false,
                            ADD_DATA_URI_TAGS: ['img'],
                            ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|tel|cid):|data:image\/(?:png|gif|jpe?g|webp|bmp|x-icon|vnd\.microsoft\.icon|avif);base64,|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
                            FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form', 'input', 'button'],
                            FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur']
                        });
                    } else {
                        // DOMPurify 未加载（CDN 不可达），回退为基本过滤
                        console.warn('DOMPurify 未加载，使用基本 HTML 过滤');
                        sanitizedBody = renderableBody
                            .replace(/<script[\s\S]*?<\/script>/gi, '')
                            .replace(/<style[\s\S]*?<\/style>/gi, '')
                            .replace(/on\w+="[^"]*"/gi, '')
                            .replace(/on\w+='[^']*'/gi, '');
                    }

                    const htmlContent = `
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <meta charset="UTF-8">
                            <style>
                                body {
                                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                                    font-size: 15px;
                                    line-height: 1.6;
                                    color: #333;
                                    margin: 0;
                                    padding: 0;
                                    background-color: transparent;
                                }
                                img { max-width: 100%; height: auto; }
                                a { color: var(--clr-primary, #2563EB); }
                            </style>
                        </head>
                        <body>${sanitizedBody}</body>
                        </html>
                    `;
                    iframe.srcdoc = htmlContent;
                }
            }
        }

        // 动态调整 iframe 高度
