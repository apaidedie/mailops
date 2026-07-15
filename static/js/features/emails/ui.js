// split from emails.js → ui.js
        function showEmailDetailContainer(options = {}) {
            const refs = getEmailDetailRefs(options);
            if (refs.source === 'mailbox') {
                if (typeof showEmailDetailSection === 'function') {
                    showEmailDetailSection();
                }
                return;
            }
            if (refs.section) {
                refs.section.style.display = 'flex';
            }
        }

        function hideEmailDetailContainer(options = {}) {
            const refs = getEmailDetailRefs(options);
            if (refs.source === 'mailbox') {
                if (typeof hideEmailDetailSection === 'function') {
                    hideEmailDetailSection();
                }
                return;
            }
            if (refs.section) {
                refs.section.style.display = 'none';
            }
        }

        function openFullscreenEmail() {
            const refs = getEmailDetailRefs();
            const emailDetail = refs.container;
            const modal = document.getElementById('fullscreenEmailModal');
            const content = document.getElementById('fullscreenEmailContent');
            const title = document.getElementById('fullscreenEmailTitle');

            if (!emailDetail) {
                return;
            }

            // 获取当前邮件的标题
            const subjectElement = emailDetail.querySelector('.email-detail-subject');
            if (subjectElement) {
                title.textContent = subjectElement.textContent;
            }

            // 克隆邮件内容
            const emailHeader = emailDetail.querySelector('.email-detail-header');
            const emailBody = emailDetail.querySelector('.email-detail-body');

            if (emailHeader && emailBody) {
                // 清空内容
                content.innerHTML = '';

                // 克隆头部信息
                const headerClone = emailHeader.cloneNode(true);
                content.appendChild(headerClone);

                // 处理邮件正文
                const iframe = emailBody.querySelector('iframe');
                const textContent = emailBody.querySelector('.email-body-text');

                if (iframe) {
                    // 如果是 HTML 邮件，创建新的 iframe
                    const newIframe = document.createElement('iframe');
                    newIframe.id = 'fullscreenEmailBodyFrame';
                    newIframe.style.width = '100%';
                    newIframe.style.border = 'none';
                    newIframe.style.backgroundColor = '#ffffff';

                    // 复制原 iframe 的内容
                    if (iframe.contentDocument) {
                        const htmlContent = iframe.contentDocument.documentElement.outerHTML;
                        newIframe.srcdoc = htmlContent;
                    }

                    content.appendChild(newIframe);

                    // 调整 iframe 高度
                    newIframe.onload = function () {
                        adjustFullscreenIframeHeight(newIframe);
                    };
                } else if (textContent) {
                    // 如果是纯文本邮件，直接克隆
                    const textClone = textContent.cloneNode(true);
                    content.appendChild(textClone);
                }

                // 显示模态框
                modal.classList.add('show');
                document.body.style.overflow = 'hidden';
            }
        }

        // 切换信任模式
        function closeFullscreenEmail() {
            const modal = document.getElementById('fullscreenEmailModal');
            modal.classList.remove('show');
            document.body.style.overflow = '';
        }

        function closeFullscreenEmailOnBackdrop(event) {
            // 只有点击背景时才关闭，点击内容区域不关闭
            if (event.target.id === 'fullscreenEmailModal') {
                closeFullscreenEmail();
            }
        }

        function showEmailList() {
            if (resolveEmailDetailSource() === 'temp') {
                if (typeof setTempDetailFocus === 'function') {
                    setTempDetailFocus(false);
                }
                currentEmailDetail = null;
                isTrustedMode = false;
                resetEmailDetailState({ source: 'temp' });
                hideEmailDetailContainer({ source: 'temp' });
                return;
            }

            setMailboxDetailFocus(false);
            syncEmailListVisibility(true);
            isListVisible = true;
            var t = document.getElementById('toggleListText');
            if (t) t.textContent = translateAppTextLocal('隐藏列表');
            if (typeof hideEmailDetailSection === 'function') {
                hideEmailDetailSection();
            }
        }

        // 刷新邮件
