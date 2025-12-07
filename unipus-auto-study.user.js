// ==UserScript==
// @name         U校园AI自动刷时长助手
// @version      4.0.1
// @description  新视野大学英语自动识别目录、自动翻页、分配课时,高效刷课工具
// @author       UXU倒計時
// @match        https://ucontent.unipus.cn/*
// @icon         https://ucontent.unipus.cn/favicon.ico
// @grant        none
// @run-at       document-end
// @homepage     https://github.com/Brandonjhd/unipus-ai
// @homepageURL  https://github.com/Brandonjhd/unipus-ai
// @supportURL   https://github.com/Brandonjhd/unipus-ai/issues
// @license      CC-BY-NC-SA-4.0
// ==/UserScript==

(function() {
    'use strict';

    let isPaused = false;
    let isRunning = false;
    let lastTimeValue = 60;
    let lastStartIdx = 0;
    let perStepTime = 0;
    let shouldRestart = false;

    function clickIKnow() {
        const btn1 = document.querySelector('.know-box .iKnow');
        if(btn1) btn1.click();
        const btn2 = document.querySelector('.ant-modal-confirm-btns .ant-btn-primary.system-info-cloud-ok-button');
        if(btn2) btn2.click();
        const btn3 = document.querySelector('.ant-modal-confirm-btns .ant-btn.ant-btn-primary');
        if(btn3) btn3.click();
    }

    function createFloatingBall() {
        let ball = document.createElement('div');
        ball.id = 'unipus-ball';
        ball.style.position = 'fixed';
        ball.style.bottom = '20px';
        ball.style.right = '20px';
        ball.style.width = '60px';
        ball.style.height = '60px';
        ball.style.borderRadius = '30px';
        ball.style.background = 'linear-gradient(135deg,#667eea 0%,#764ba2 100%)';
        ball.style.zIndex = '99999';
        ball.style.boxShadow = '0 4px 15px rgba(102,126,234,0.4)';
        ball.style.display = 'flex';
        ball.style.justifyContent = 'center';
        ball.style.alignItems = 'center';
        ball.style.cursor = 'pointer';
        ball.style.fontSize = '24px';
        ball.style.transition = 'all 0.3s ease';
        ball.innerText = '🎓';
        ball.title = '点击展开U校园AI自动刷时长助手';
        document.body.appendChild(ball);

        ball.onmouseenter = function(){
            this.style.transform = 'scale(1.1)';
            this.style.boxShadow = '0 6px 20px rgba(102,126,234,0.6)';
        };
        ball.onmouseleave = function(){
            this.style.transform = 'scale(1)';
            this.style.boxShadow = '0 4px 15px rgba(102,126,234,0.4)';
        };

        ball.onclick = function() {
            let panel = document.getElementById('unipus-panel');
            if(panel) { panel.style.display = (panel.style.display=='none' ? 'block' : 'none'); return;}
            createControlPanel();
        };
    }

    function getMenuList() {
        let nodes = [];
        let menuContainer = document.querySelector('.pc-slier-menu-container.show .pc-slider-content-menu');
        if(!menuContainer) return [];
        menuContainer.querySelectorAll('.pc-slider-menu-unit').forEach(unit=>{
            let unitName = unit.querySelector('.unit-label-item')?.title || '';
            unit.parentElement.querySelectorAll('.pc-slider-menu-section').forEach(section=>{
                let sectionName = section.querySelector('span')?.title || '';
                section.parentElement.querySelectorAll('.pc-slider-menu-micro').forEach(micro=>{
                    let microName = micro.querySelector('.pc-menu-node-name')?.title || '';
                    let microElem = micro.querySelector('.pc-menu-node-name');
                    nodes.push({
                        unit: unitName,
                        section: sectionName,
                        micro: microName,
                        element: microElem
                    });
                });
            });
        });
        return nodes;
    }

    function waitForElement(selector, timeout = 3000) {
        return new Promise((resolve) => {
            const startTime = Date.now();
            const checkExist = setInterval(() => {
                clickIKnow();
                if(shouldRestart) {
                    clearInterval(checkExist);
                    resolve(null);
                    return;
                }
                const element = document.querySelector(selector);
                if (element || Date.now() - startTime > timeout) {
                    clearInterval(checkExist);
                    resolve(element);
                }
            }, 100);
        });
    }

    function getTabs() {
        let tabs = [];
        let tabContainers = document.querySelectorAll('.pc-header-tabs-container .ant-col');
        tabContainers.forEach((tab)=>{
            let nameElem = tab.querySelector('.pc-tab-view-container');
            if(nameElem && tab.classList.contains('tab')){
                tabs.push({
                    name: nameElem.title || nameElem.innerText,
                    element: nameElem
                });
            }
        });
        return tabs;
    }

    function getTasks() {
        let tasks = [];
        document.querySelectorAll('.pc-header-tasks-row .pc-task').forEach((task)=>{
            tasks.push({
                name: task.title || task.innerText,
                element: task
            });
        });
        return tasks;
    }

    function addLog(message, isCountdown = false) {
        const log = document.getElementById('unipus-log');
        if(!log) return;

        if(isCountdown) {
            const lastChild = log.lastElementChild;
            if(lastChild && lastChild.classList.contains('countdown-line')) {
                lastChild.textContent = message;
            } else {
                const div = document.createElement('div');
                div.className = 'countdown-line';
                div.textContent = message;
                log.appendChild(div);
            }
        } else {
            const div = document.createElement('div');
            div.textContent = message;
            log.appendChild(div);
        }
        log.scrollTop = log.scrollHeight;
    }

    function addPauseLog(message) {
        const log = document.getElementById('unipus-log');
        if(!log) return;

        const pauseLine = log.querySelector('.pause-line');
        if(pauseLine) {
            pauseLine.remove();
        }

        const div = document.createElement('div');
        div.className = 'pause-line';
        div.textContent = message;
        log.appendChild(div);
        log.scrollTop = log.scrollHeight;
    }

    function removePauseLine() {
        const log = document.getElementById('unipus-log');
        if(!log) return;
        const pauseLine = log.querySelector('.pause-line');
        if(pauseLine) {
            pauseLine.remove();
        }
    }

    function removeCountdownLine() {
        const log = document.getElementById('unipus-log');
        if(!log) return;
        const countdownLine = log.querySelector('.countdown-line');
        if(countdownLine) {
            countdownLine.remove();
        }
    }

    function createControlPanel() {
        let panel = document.createElement('div');
        panel.id = 'unipus-panel';
        panel.style.position = 'fixed';
        panel.style.right = '20px';
        panel.style.bottom = '90px';
        panel.style.width = '380px';
        panel.style.background = 'linear-gradient(135deg,#667eea 0%,#764ba2 100%)';
        panel.style.border = 'none';
        panel.style.boxShadow = '0 8px 32px rgba(0,0,0,0.3)';
        panel.style.borderRadius = '16px';
        panel.style.zIndex = '99999';
        panel.style.fontFamily = 'sans-serif';
        panel.style.padding = '20px';
        panel.style.display = 'block';

        let title = document.createElement('div');
        title.innerHTML = '📚 U校园AI自动刷时长助手';
        title.style.fontSize = '18px';
        title.style.fontWeight = 'bold';
        title.style.color = '#fff';
        title.style.marginBottom = '8px';
        title.style.textAlign = 'center';

        let authorInfo = document.createElement('div');
        authorInfo.style.display = 'flex';
        authorInfo.style.alignItems = 'center';
        authorInfo.style.justifyContent = 'space-between';
        authorInfo.style.marginBottom = '2px';
        authorInfo.style.paddingBottom = '2px';

        let authorText = document.createElement('p');
        authorText.textContent = '作者: UXU倒計時';
        authorText.style.margin = '0';
        authorText.style.fontSize = '12px';
        authorText.style.color = 'rgba(255,255,255,0.9)';

        let githubLink = document.createElement('a');
        githubLink.href = 'https://github.com/Brandonjhd/unipus-ai';
        githubLink.textContent = '📦 GitHub仓库';
        githubLink.style.fontSize = '12px';
        githubLink.style.color = '#fff';

        authorInfo.appendChild(authorText);
        authorInfo.appendChild(githubLink);

        let contentBox = document.createElement('div');
        contentBox.style.background = '#fff';
        contentBox.style.borderRadius = '12px';
        contentBox.style.padding = '16px';

        let menuList = getMenuList();
        let menuLabel = document.createElement('label');
        menuLabel.innerHTML = '📖 选择起始目录:';
        menuLabel.style.display = 'block';
        menuLabel.style.marginBottom = '8px';
        menuLabel.style.fontSize = '14px';
        menuLabel.style.fontWeight = '600';
        menuLabel.style.color = '#333';

        let menuSelect = document.createElement('select');
        menuSelect.id = 'unipus-menu-select';
        menuSelect.style.width = '100%';
        menuSelect.style.padding = '8px';
        menuSelect.style.borderRadius = '8px';
        menuSelect.style.border = '2px solid #e0e0e0';
        menuSelect.style.fontSize = '13px';
        menuSelect.style.marginBottom = '15px';
        menuList.forEach((item,i)=>{
            let op = document.createElement('option');
            op.value = i;
            op.text = `${item.unit} > ${item.section} > ${item.micro}`;
            menuSelect.appendChild(op);
        });

        let timeLabel = document.createElement('label');
        timeLabel.innerHTML = '⏱️ 总刷课时长(分钟):';
        timeLabel.style.display = 'block';
        timeLabel.style.marginBottom = '8px';
        timeLabel.style.fontSize = '14px';
        timeLabel.style.fontWeight = '600';
        timeLabel.style.color = '#333';

        let timeInput = document.createElement('input');
        timeInput.type = 'number';
        timeInput.value = 60;
        timeInput.style.width = '100%';
        timeInput.style.padding = '8px';
        timeInput.style.borderRadius = '8px';
        timeInput.style.border = '2px solid #e0e0e0';
        timeInput.style.fontSize = '14px';
        timeInput.style.marginBottom = '15px';
        timeInput.min = 1;
        timeInput.id = 'unipus-time-input';

        let btnContainer = document.createElement('div');
        btnContainer.style.display = 'flex';
        btnContainer.style.gap = '10px';
        btnContainer.style.marginBottom = '15px';

        let startBtn = document.createElement('button');
        startBtn.innerHTML = '🚀 开始刷课';
        startBtn.style.flex = '1';
        startBtn.style.padding = '12px';
        startBtn.style.background = 'linear-gradient(135deg,#667eea 0%,#764ba2 100%)';
        startBtn.style.color = '#fff';
        startBtn.style.borderRadius = '8px';
        startBtn.style.border = 'none';
        startBtn.style.fontSize = '15px';
        startBtn.style.fontWeight = 'bold';
        startBtn.style.cursor = 'pointer';
        startBtn.style.transition = 'all 0.3s ease';

        let pauseBtn = document.createElement('button');
        pauseBtn.innerHTML = '⏸️ 暂停';
        pauseBtn.style.flex = '1';
        pauseBtn.style.padding = '12px';
        pauseBtn.style.background = '#ffa500';
        pauseBtn.style.color = '#fff';
        pauseBtn.style.borderRadius = '8px';
        pauseBtn.style.border = 'none';
        pauseBtn.style.fontSize = '15px';
        pauseBtn.style.fontWeight = 'bold';
        pauseBtn.style.cursor = 'pointer';
        pauseBtn.style.transition = 'all 0.3s ease';
        pauseBtn.style.display = 'none';

        let log = document.createElement('div');
        log.id = 'unipus-log';
        log.style.height = '120px';
        log.style.overflowY = 'auto';
        log.style.fontSize = '12px';
        log.style.border = '2px solid #e0e0e0';
        log.style.background = '#f9f9f9';
        log.style.padding = '10px';
        log.style.borderRadius = '8px';
        log.style.fontFamily = 'monospace';
        log.style.color = '#555';

        btnContainer.appendChild(startBtn);
        btnContainer.appendChild(pauseBtn);

        contentBox.appendChild(menuLabel);
        contentBox.appendChild(menuSelect);
        contentBox.appendChild(timeLabel);
        contentBox.appendChild(timeInput);
        contentBox.appendChild(btnContainer);
        contentBox.appendChild(log);

        panel.appendChild(title);
        panel.appendChild(authorInfo);
        panel.appendChild(contentBox);

        document.body.appendChild(panel);

        pauseBtn.onclick = function(){
            isPaused = !isPaused;
            if(isPaused){
                pauseBtn.innerHTML = '▶️ 继续';
                pauseBtn.style.background = '#28a745';
                addPauseLog('⏸️ 已暂停');
            } else {
                pauseBtn.innerHTML = '⏸️ 暂停';
                pauseBtn.style.background = '#ffa500';
                removePauseLine();

                const currentTimeValue = Math.max(1, +timeInput.value);
                const currentStartIdx = +menuSelect.value;

                if(currentTimeValue !== lastTimeValue || currentStartIdx !== lastStartIdx) {
                    removeCountdownLine();
                    const jobs = menuList.slice(currentStartIdx);
                    const totalSeconds = currentTimeValue * 60;
                    perStepTime = totalSeconds / jobs.length;
                    addLog(`⚙️ 配置已修改,立即跳转: 共${jobs.length}个目录,每个约${Math.round(perStepTime)}秒`);
                    lastTimeValue = currentTimeValue;
                    lastStartIdx = currentStartIdx;
                    shouldRestart = true;
                } else {
                    addLog('▶️ 继续运行');
                }
            }
        };

        startBtn.onclick = function(){
            if(isRunning) {
                addLog('⚠️ 已经在运行中...');
                return;
            }
            isRunning = true;
            isPaused = false;
            shouldRestart = false;
            startBtn.style.display = 'none';
            pauseBtn.style.display = 'block';
            pauseBtn.innerHTML = '⏸️ 暂停';
            pauseBtn.style.background = '#ffa500';

            lastTimeValue = Math.max(1, +timeInput.value);
            lastStartIdx = +menuSelect.value;
            let jobs = menuList.slice(lastStartIdx);
            const totalSeconds = lastTimeValue * 60;
            perStepTime = totalSeconds / jobs.length;

            (async function loop(){
                addLog(`共${jobs.length}个目录,每个约${Math.round(perStepTime)}秒`);

                for(let idx=0; isRunning && idx < jobs.length; idx++){
                    while(isPaused && isRunning){
                        await new Promise(rs=>setTimeout(rs,500));
                        if(shouldRestart) break;
                    }

                    if(shouldRestart) {
                        shouldRestart = false;
                        const newStartIdx = +menuSelect.value;
                        jobs = menuList.slice(newStartIdx);
                        idx = -1;
                        clickIKnow();
                        if(jobs[0]?.element) {
                            jobs[0].element.click();
                        }
                        await new Promise(rs=>setTimeout(rs,2000));
                        addLog(`🔄 已跳转到: [${newStartIdx+1}] ${jobs[0]?.micro || ''}`);
                        continue;
                    }

                    if(!isRunning || isPaused) continue;

                    clickIKnow();
                    addLog(`📂 [${lastStartIdx + idx + 1}/${menuList.length}] ${jobs[idx].micro}`);

                    if(jobs[idx].element) {
                        clickIKnow();
                        jobs[idx].element.click();
                        clickIKnow();
                    }

                    if(shouldRestart) continue;
                    await new Promise(rs=>setTimeout(rs,2000));
                    if(shouldRestart) continue;

                    clickIKnow();
                    await waitForElement('.pc-header-tabs-container', 3000);
                    if(shouldRestart) continue;

                    clickIKnow();
                    const tabs = getTabs();
                    const tasks = getTasks();

                    let totalSteps = 0;
                    if(tabs.length > 0) {
                        for(let t=0; t<tabs.length; t++) {
                            if(shouldRestart) break;
                            clickIKnow();
                            if(tabs[t].element) tabs[t].element.click();
                            clickIKnow();
                            await new Promise(rs=>setTimeout(rs,1500));
                            if(shouldRestart) break;
                            await waitForElement('.pc-header-tasks-row', 2000);
                            if(shouldRestart) break;
                            const tabTasks = getTasks();
                            totalSteps += tabTasks.length > 0 ? tabTasks.length : 1;
                        }
                    } else {
                        totalSteps = tasks.length > 0 ? tasks.length : 1;
                    }

                    if(shouldRestart) continue;
                    const stepTime = perStepTime / totalSteps;

                    if(tabs.length > 0){
                        for(let t=0; t<tabs.length; t++){
                            if(shouldRestart) break;
                            while(isPaused && isRunning){
                                await new Promise(rs=>setTimeout(rs,500));
                                if(shouldRestart) break;
                            }
                            if(!isRunning || shouldRestart) break;
                            if(isPaused) continue;

                            clickIKnow();
                            addLog(`📑 Tab[${t+1}/${tabs.length}]: ${tabs[t].name}`);

                            if(tabs[t].element) {
                                clickIKnow();
                                tabs[t].element.click();
                                clickIKnow();
                            }

                            if(shouldRestart) break;
                            await new Promise(rs=>setTimeout(rs,2000));
                            if(shouldRestart) break;
                            clickIKnow();
                            await waitForElement('.pc-header-tasks-row', 3000);
                            if(shouldRestart) break;
                            clickIKnow();

                            const tabTasks = getTasks();
                            if(tabTasks.length > 0){
                                for(let k=0; k<tabTasks.length; k++){
                                    if(shouldRestart) break;
                                    while(isPaused && isRunning){
                                        await new Promise(rs=>setTimeout(rs,500));
                                        if(shouldRestart) break;
                                    }
                                    if(!isRunning || shouldRestart) break;
                                    if(isPaused) continue;

                                    const taskName = `✏️ Task[${k+1}/${tabTasks.length}]: ${tabTasks[k].name}`;
                                    clickIKnow();
                                    if(tabTasks[k].element) {
                                        clickIKnow();
                                        tabTasks[k].element.click();
                                        clickIKnow();
                                    }
                                    await waitTime(stepTime, taskName);
                                    if(shouldRestart) break;
                                    clickIKnow();
                                }
                                if(shouldRestart) break;
                            } else {
                                await waitTime(stepTime, '');
                                if(shouldRestart) break;
                                clickIKnow();
                            }
                        }
                        if(shouldRestart) continue;
                    } else {
                        const directTasks = getTasks();
                        if(directTasks.length > 0){
                            for(let k=0; k<directTasks.length; k++){
                                if(shouldRestart) break;
                                while(isPaused && isRunning){
                                    await new Promise(rs=>setTimeout(rs,500));
                                    if(shouldRestart) break;
                                }
                                if(!isRunning || shouldRestart) break;
                                if(isPaused) continue;

                                const taskName = `✏️ Task[${k+1}/${directTasks.length}]: ${directTasks[k].name}`;
                                clickIKnow();
                                if(directTasks[k].element) {
                                    clickIKnow();
                                    directTasks[k].element.click();
                                    clickIKnow();
                                }
                                await waitTime(stepTime, taskName);
                                if(shouldRestart) break;
                                clickIKnow();
                            }
                            if(shouldRestart) continue;
                        } else {
                            await waitTime(perStepTime, '');
                            if(shouldRestart) continue;
                            clickIKnow();
                        }
                    }
                }
                addLog('🎉 刷课完成!');
                isRunning = false;
                startBtn.style.display = 'block';
                pauseBtn.style.display = 'none';
                startBtn.innerHTML = '🚀 开始刷课';
            })();
        };
    }

    async function waitTime(seconds, taskName){
        let remaining = Math.round(seconds);

        while(remaining > 0){
            while(isPaused && isRunning){
                await new Promise(rs=>setTimeout(rs,500));
                if(shouldRestart) break;
            }
            if(!isRunning || isPaused || shouldRestart) break;

            clickIKnow();

            if(taskName){
                addLog(`${taskName} ⏳${remaining}秒`, true);
            }

            await new Promise(rs=>setTimeout(rs,1000));
            remaining--;
        }

        if(taskName && !shouldRestart){
            const log = document.getElementById('unipus-log');
            const countdownLine = log?.querySelector('.countdown-line');
            if(countdownLine) {
                countdownLine.remove();
            }
            addLog(taskName);
        } else if(shouldRestart) {
            removeCountdownLine();
        }
    }

    window.addEventListener('load',function(){
        setTimeout(()=>{
            createFloatingBall();
            clickIKnow();
        },1600);
    });

})();
