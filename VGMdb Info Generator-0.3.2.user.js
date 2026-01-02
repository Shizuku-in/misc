// ==UserScript==
// @name         VGMdb Info Generator
// @name:zh-CN   VGMdb 信息生成
// @namespace    https://vgmdb.net/
// @version      0.3.2
// @description  VGMdb BBcode-style album information generator
// @description:zh-cn VGMdb BBcode 样式专辑信息生成
// @author       gkouen
// @license      MIT
// @homepage     https://blog.cya.moe/
// @match        *://vgmdb.net/album/*
// @icon         https://vgmdb.net/favicon.ico
// @grant        GM_setClipboard
// @downloadURL https://update.greasyfork.org/scripts/523046/VGMdb%20Info%20Generator.user.js
// @updateURL https://update.greasyfork.org/scripts/523046/VGMdb%20Info%20Generator.meta.js
// ==/UserScript==

(function () {
    'use strict';

    const discussSpan = document.querySelector('span.label.smallfont > span#albumtools');
    if (!discussSpan) return;

    // Info button
    const generateInfoButton = document.createElement('a');
    generateInfoButton.textContent = 'Info';
    generateInfoButton.style.cursor = 'pointer';
    generateInfoButton.style.marginLeft = '0px';
    generateInfoButton.style.color = '#ceffff';
    generateInfoButton.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        generateInfo();
    });

    // Format button
    const formatButton = document.createElement('a');
    formatButton.textContent = 'Format';
    formatButton.style.cursor = 'pointer';
    formatButton.style.marginLeft = '0px';
    formatButton.style.color = '#ceffff';
    formatButton.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        formatInfo(formatButton);
    });

    const separator1 = document.createTextNode(' | ');
    const separator2 = document.createTextNode(' | ');
    discussSpan.appendChild(separator1);
    discussSpan.appendChild(generateInfoButton);
    discussSpan.appendChild(separator2);
    discussSpan.appendChild(formatButton);

    const months = { Jan: '01', Feb: '02', Mar: '03', Apr: '04', May: '05', Jun: '06', Jul: '07', Aug: '08', Sep: '09', Oct: '10', Nov: '11', Dec: '12' };

function generateInfo() {
    try {
        const coverArt = document.querySelector('#coverart').style.backgroundImage.match(/url\("?(.*?)"?\)/)?.[1];
        const title = getAlbumTitle();
        const catalogNumber = getSiblingValue('Catalog Number');
        const releaseDate = getSiblingValue('Release Date');
        const formattedDate = formatDate(releaseDate);

        const japaneseTab = Array.from(document.querySelectorAll('a[rel^="tl"]'))
            .find(a => a.textContent.trim().toLowerCase() === 'japanese');

        let tracklist = '';

        if (japaneseTab) {
            const relId = japaneseTab.getAttribute('rel');
            const tracklistContainer = document.querySelector(`span.tl#${relId}`);
            if (tracklistContainer) {
                const trackRows = tracklistContainer.querySelectorAll('tr.rolebit');
                tracklist = Array.from(trackRows)
                    .map(row => {
                        const trackNumber = row.querySelector('.label')?.textContent.trim();
                        const trackName = row.querySelector('td[width="100%"]')?.textContent.trim();
                        return `${trackNumber}\t${trackName}`;
                    })
                    .join('\n');
            }
        } else {
            console.warn('No Japanese tracklist found!');
        }

        const resultText = `[quote]
[img]${coverArt}[/img]
[b]Title:[/b] ${title}
[b]Catalog number:[/b] ${catalogNumber}
[b]Release date:[/b] ${formattedDate}
[b]Tracklist[/b]:
[code]
${tracklist}
[/code]
[/quote]`;

        showTemporaryModal(resultText);
    } catch (error) {
        console.error('Error:', error);
        alert('Error occurred, please check the console log!');
    }
}


    function formatInfo(buttonElement) {
        try {
            const title = getAlbumTitle();
            const releaseDate = getSiblingValue('Release Date');
            const formattedDate = formatDateForClipboard(releaseDate);

            const sanitizedTitle = sanitizeTitle(title);

            const formattedText = `[${formattedDate}]${sanitizedTitle}`;
            GM_setClipboard(formattedText);

            showTemporaryTooltip(buttonElement, 'Copied to clipboard');
        } catch (error) {
            console.error('Error:', error);
        }
    }

    function getAlbumTitle() {
        const jpnTitle = document.querySelector('.albumtitle[lang="ja"]');
        const engTitle = document.querySelector('.albumtitle[lang="en"]');
        const title = jpnTitle?.textContent.trim() || engTitle?.textContent.trim() || 'Unknown';
        return title;
    }

    function sanitizeTitle(title) {
        return title
            .replace(/^\s*\/|\/\s*$/g, '')
            .replace(/\//g, '／')
            .replace(/:/g, '：')
            .replace(/\*/g, '＊')
            .replace(/\?/g, '？')
            .replace(/"/g, '＂')
            .replace(/</g, '＜')
            .replace(/>/g, '＞')
            .replace(/\|/g, '｜');
    }

    function getSiblingValue(labelText) {
        const labelCell = Array.from(document.querySelectorAll('#album_infobit_large td'))
            .find(td => td.textContent.trim() === labelText);
        return labelCell ? labelCell.nextElementSibling.textContent.trim() : '';
    }

    function formatDate(dateString) {
        if (!dateString) return 'Unknown Date';
        const [month, day, year] = dateString.split(' ');
        return `${year}/${months[month]}/${day.replace(',', '')}`;
    }

    function formatDateForClipboard(dateString) {
        if (!dateString) return 'Unknown Date';
        const [month, day, year] = dateString.split(' ');
        return `${year.substring(2)}${months[month]}${day.replace(',', '')}`;
    }

    function showTemporaryTooltip(buttonElement, message) {
        const tooltip = document.createElement('div');
        tooltip.textContent = message;
        tooltip.style.position = 'absolute';
        tooltip.style.backgroundColor = '#000';
        tooltip.style.color = '#fff';
        tooltip.style.padding = '5px 10px';
        tooltip.style.borderRadius = '5px';
        tooltip.style.fontSize = '12px';
        tooltip.style.opacity = '0';
        tooltip.style.transition = 'opacity 0.5s';
        tooltip.style.zIndex = '1000';

        const rect = buttonElement.getBoundingClientRect();
        tooltip.style.left = `${rect.left + window.scrollX}px`;
        tooltip.style.top = `${rect.bottom + window.scrollY + 5}px`;

        document.body.appendChild(tooltip);

        requestAnimationFrame(() => {
            tooltip.style.opacity = '1';
        });

        setTimeout(() => {
            tooltip.style.opacity = '0';
            setTimeout(() => {
                tooltip.remove();
            }, 500);
        }, 500);
    }

    function showTemporaryModal(text) {
        const modal = document.createElement('div');
        modal.style.position = 'fixed';
        modal.style.top = '50%';
        modal.style.left = '50%';
        modal.style.transform = 'translate(-50%, -50%)';
        modal.style.backgroundColor = '#fff';
        modal.style.padding = '20px';
        modal.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
        modal.style.zIndex = '9999';
        modal.style.opacity = '0';
        modal.style.transition = 'opacity 0.5s';

        const textarea = document.createElement('textarea');
        textarea.style.width = '500px';
        textarea.style.height = '300px';
        textarea.textContent = text;

        const closeButton = document.createElement('button');
        closeButton.textContent = 'Close';
        closeButton.style.marginTop = '10px';
        closeButton.addEventListener('click', () => {
            modal.style.opacity = '0';
            setTimeout(() => {
                modal.remove();
            }, 500);
        });

        modal.appendChild(textarea);
        modal.appendChild(closeButton);
        document.body.appendChild(modal);

        requestAnimationFrame(() => {
            modal.style.opacity = '1';
        });
    }
})();
