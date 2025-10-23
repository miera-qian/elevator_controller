/**
 * 控制面板视图
 * 职责：管理控制面板UI的渲染和交互
 */
class ControlPanelView {
    constructor() {
        // DOM 元素引用
        this.elements = {
            algorithmSelect: document.getElementById('algorithm-select'),
            algorithmDescription: document.getElementById('algorithm-description'),
            scenarioSelect: document.getElementById('scenario-select'),
            scenarioInfo: document.getElementById('scenario-info'),
            speedSlider: document.getElementById('speed-slider'),
            speedValue: document.getElementById('speed-value'),
            startBtn: document.getElementById('start-btn'),
            pauseBtn: document.getElementById('pause-btn'),
            resumeBtn: document.getElementById('resume-btn'),
            stopBtn: document.getElementById('stop-btn'),
            statusMessage: document.getElementById('status-message'),
            stats: {
                tick: document.getElementById('stat-tick'),
                total: document.getElementById('stat-total'),
                waiting: document.getElementById('stat-waiting'),
                inElevator: document.getElementById('stat-in-elevator'),
                completed: document.getElementById('stat-completed'),
                avgWait: document.getElementById('stat-avg-wait')
            }
        };

        // 事件回调（由Controller设置）
        this.onAlgorithmChange = null;
        this.onScenarioChange = null;
        this.onStartClick = null;
        this.onPauseClick = null;
        this.onResumeClick = null;
        this.onStopClick = null;
        this.onSpeedChange = null;

        // 最终统计数据锁定（模拟完成后保留数据）
        this.finalStatsLocked = false;
        this.finalStats = null;

        this._bindEvents();
    }

    /**
     * 绑定 DOM 事件
     * @private
     */
    _bindEvents() {
        this.elements.algorithmSelect.addEventListener('change', (e) => {
            if (this.onAlgorithmChange) {
                this.onAlgorithmChange(e.target.value);
            }
        });

        this.elements.scenarioSelect.addEventListener('change', (e) => {
            if (this.onScenarioChange) {
                this.onScenarioChange(e.target.value);
            }
        });

        this.elements.startBtn.addEventListener('click', () => {
            if (this.onStartClick) {
                this.onStartClick();
            }
        });

        this.elements.pauseBtn.addEventListener('click', () => {
            if (this.onPauseClick) {
                this.onPauseClick();
            }
        });

        this.elements.resumeBtn.addEventListener('click', () => {
            if (this.onResumeClick) {
                this.onResumeClick();
            }
        });

        this.elements.stopBtn.addEventListener('click', () => {
            if (this.onStopClick) {
                this.onStopClick();
            }
        });

        this.elements.speedSlider.addEventListener('input', (e) => {
            const speed = parseFloat(e.target.value);
            this.elements.speedValue.textContent = `${speed.toFixed(1)}x`;

            if (this.onSpeedChange) {
                this.onSpeedChange(speed);
            }
        });
    }

    /**
     * 渲染算法列表
     * @param {Array} algorithms - 算法列表
     */
    renderAlgorithms(algorithms) {
        this.elements.algorithmSelect.innerHTML = '';

        algorithms.forEach(algo => {
            const option = document.createElement('option');
            option.value = algo.name;
            option.textContent = algo.display_name;
            this.elements.algorithmSelect.appendChild(option);
        });
    }

    /**
     * 显示算法描述
     * @param {Object} algorithm - 算法信息
     */
    showAlgorithmDescription(algorithm) {
        this.elements.algorithmDescription.innerHTML = `
            <strong>${algorithm.type}</strong><br>
            ${algorithm.description}
        `;
    }

    /**
     * 渲染场景列表
     * @param {Array} scenarios - 场景列表
     */
    renderScenarios(scenarios) {
        this.elements.scenarioSelect.innerHTML = '';

        scenarios.forEach(scenario => {
            const option = document.createElement('option');
            option.value = scenario.name;
            option.textContent = scenario.display_name;
            this.elements.scenarioSelect.appendChild(option);
        });
    }

    /**
     * 显示场景信息
     * @param {Object} scenario - 场景信息
     */
    showScenarioInfo(scenario) {
        this.elements.scenarioInfo.innerHTML = `
            <div class="info-row">
                <span class="info-label">楼层数:</span>
                <span class="info-value">${scenario.floors}</span>
            </div>
            <div class="info-row">
                <span class="info-label">电梯数:</span>
                <span class="info-value">${scenario.elevators}</span>
            </div>
            <div class="info-row">
                <span class="info-label">乘客数:</span>
                <span class="info-value">${scenario.passengers}</span>
            </div>
            <div class="info-row">
                <span class="info-label">时长:</span>
                <span class="info-value">${scenario.duration}s</span>
            </div>
            <div class="info-row">
                <span class="info-label">类型:</span>
                <span class="info-value">${scenario.type}</span>
            </div>
        `;
    }

    /**
     * 更新统计数据显示
     * @param {Object} stats - 统计数据
     */
    updateStats(message) {
        // 如果最终统计已锁定，不再更新（保留完成时的数据）
        if (this.finalStatsLocked) {
            return;
        }

        if (message.tick !== undefined) {
            this.elements.stats.tick.textContent = message.tick;
        }

        if (message.stats) {
            const stats = message.stats;

            if (stats.total_passengers !== undefined) {
                this.elements.stats.total.textContent = stats.total_passengers;
            }
            if (stats.waiting !== undefined) {
                this.elements.stats.waiting.textContent = stats.waiting;
            }
            if (stats.in_elevator !== undefined) {
                this.elements.stats.inElevator.textContent = stats.in_elevator;
            }
            if (stats.completed !== undefined) {
                this.elements.stats.completed.textContent = stats.completed;
            }
            if (stats.avg_wait_time !== undefined) {
                this.elements.stats.avgWait.textContent = stats.avg_wait_time.toFixed(2);
            }
        }
    }

    /**
     * 显示最终统计数据（高亮显示）
     * @param {Object} stats - 最终统计数据
     */
    showFinalStats(stats) {
        console.log('[ControlPanelView] Showing final stats:', stats);

        // 锁定最终统计数据，防止被后续更新覆盖
        this.finalStatsLocked = true;
        this.finalStats = stats;

        // 添加高亮效果
        const statsContainer = document.querySelector('.stats-panel');
        if (statsContainer) {
            statsContainer.classList.add('stats-highlight');

            // 3秒后移除高亮
            setTimeout(() => {
                statsContainer.classList.remove('stats-highlight');
            }, 3000);
        }

        // 如果有 p95 等待时间，可以在控制台显示
        if (stats.p95_wait_time !== undefined) {
            console.log(`[Final Stats] P95 Wait Time: ${stats.p95_wait_time.toFixed(2)}s`);
        }
    }

    /**
     * 重置统计数据锁定（开始新模拟时调用）
     */
    unlockStats() {
        this.finalStatsLocked = false;
        this.finalStats = null;
    }

    /**
     * 显示状态消息
     * @param {string} message - 消息内容
     * @param {string} type - 消息类型 ('info', 'success', 'error')
     */
    showStatus(message, type = 'info') {
        this.elements.statusMessage.textContent = message;
        this.elements.statusMessage.className = `status-message ${type}`;

        if (type !== 'error') {
            setTimeout(() => {
                this.elements.statusMessage.className = 'status-message';
            }, 5000);
        }
    }

    /**
     * 设置模拟运行状态
     * @param {boolean} isRunning - 是否正在运行
     */
    setSimulationState(isRunning) {
        this.elements.startBtn.disabled = isRunning;
        this.elements.pauseBtn.disabled = !isRunning;
        this.elements.stopBtn.disabled = !isRunning;
        this.elements.algorithmSelect.disabled = isRunning;
        this.elements.scenarioSelect.disabled = isRunning;
    }

    /**
     * 设置暂停状态
     * @param {boolean} isPaused - 是否暂停
     */
    setPauseState(isPaused) {
        this.elements.pauseBtn.disabled = isPaused;
        this.elements.resumeBtn.disabled = !isPaused;
    }
}
