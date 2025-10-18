/**
 * 模拟控制器
 * 职责：协调 Model 和 View，处理业务逻辑
 */
class SimulationController {
    constructor(algorithmModel, scenarioModel, controlPanelView, visualizationView) {
        // 依赖注入
        this.algorithmModel = algorithmModel;
        this.scenarioModel = scenarioModel;
        this.controlPanelView = controlPanelView;
        this.visualizationView = visualizationView;

        // WebSocket 管理器
        this.wsManager = new WebSocketManager();

        // 状态
        this.isSimulating = false;

        // 绑定 View 的事件回调
        this._bindViewEvents();

        // 绑定 WebSocket 事件
        this._bindWebSocketEvents();
    }

    /**
     * 初始化应用
     */
    async initialize() {
        try {
            console.log('[SimulationController] Initializing...');

            // 加载数据（Model 层）
            await this.algorithmModel.loadAlgorithms();
            await this.scenarioModel.loadScenarios();

            console.log('[SimulationController] Data loaded');

            // 更新 UI（View 层）
            this.controlPanelView.renderAlgorithms(this.algorithmModel.getAllAlgorithms());
            this.controlPanelView.renderScenarios(this.scenarioModel.getAllScenarios());

            // 显示默认选择
            this._updateAlgorithmDisplay();
            this._updateScenarioDisplay();

            // 初始化可视化
            const scenario = this.scenarioModel.getSelectedScenario();
            if (scenario) {
                this.visualizationView.initialize({
                    floors: scenario.floors,
                    elevators: scenario.elevators,
                    capacity: scenario.capacity || 8
                });
                console.log('[SimulationController] Visualization initialized');
            }

            this.controlPanelView.showStatus('应用已就绪，请选择算法和场景后点击"开始模拟"', 'info');
            console.log('[SimulationController] Initialization complete');

        } catch (error) {
            console.error('[SimulationController] Initialization failed:', error);
            this.controlPanelView.showStatus('初始化失败', 'error');
        }
    }

    /**
     * 绑定 View 事件到 Controller 方法
     * @private
     */
    _bindViewEvents() {
        this.controlPanelView.onAlgorithmChange = (algorithmName) => {
            this._handleAlgorithmChange(algorithmName);
        };

        this.controlPanelView.onScenarioChange = (scenarioName) => {
            this._handleScenarioChange(scenarioName);
        };

        this.controlPanelView.onStartClick = () => {
            this._handleStartSimulation();
        };

        this.controlPanelView.onPauseClick = () => {
            this._handlePauseSimulation();
        };

        this.controlPanelView.onResumeClick = () => {
            this._handleResumeSimulation();
        };

        this.controlPanelView.onStopClick = () => {
            this._handleStopSimulation();
        };

        this.controlPanelView.onSpeedChange = (speed) => {
            this._handleSpeedChange(speed);
        };
    }

    /**
     * 绑定 WebSocket 事件
     * @private
     */
    _bindWebSocketEvents() {
        this.wsManager.on('init', (message) => {
            console.log('[SimulationController] Simulation initialized:', message);
            this.visualizationView.initialize(message.building);
            this.controlPanelView.showStatus(`模拟已启动: ${message.algorithm}`, 'success');
        });

        this.wsManager.on('state_update', (message) => {
            this.visualizationView.updateState(message);
            this.controlPanelView.updateStats(message);
        });

        this.wsManager.on('complete', (message) => {
            console.log('[SimulationController] Simulation complete:', message);
            this.visualizationView.handleCompletion();
            this.controlPanelView.showStatus('模拟已完成', 'success');
            this._handleStopSimulation();
        });

        this.wsManager.on('error', (message) => {
            console.error('[SimulationController] Simulation error:', message);
            this.controlPanelView.showStatus(`错误: ${message.message}`, 'error');
        });
    }

    /**
     * 处理算法选择变化
     * @private
     */
    _handleAlgorithmChange(algorithmName) {
        // 更新 Model
        this.algorithmModel.selectAlgorithm(algorithmName);

        // 更新 View
        this._updateAlgorithmDisplay();
    }

    /**
     * 处理场景选择变化
     * @private
     */
    _handleScenarioChange(scenarioName) {
        // 更新 Model
        this.scenarioModel.selectScenario(scenarioName);

        // 更新 View
        this._updateScenarioDisplay();

        // 更新可视化配置
        const scenario = this.scenarioModel.getSelectedScenario();
        if (scenario) {
            this.visualizationView.initialize({
                floors: scenario.floors,
                elevators: scenario.elevators,
                capacity: scenario.capacity || 8
            });
            console.log('[SimulationController] Scenario changed, visualization updated:', scenario.name);
        }
    }

    /**
     * 处理开始模拟
     * @private
     */
    async _handleStartSimulation() {
        const algorithm = this.algorithmModel.getSelectedAlgorithm();
        const scenario = this.scenarioModel.getSelectedScenario();

        // 验证（业务逻辑）
        if (!algorithm || !scenario) {
            this.controlPanelView.showStatus('请选择算法和场景', 'error');
            return;
        }

        try {
            // 重置统计数据显示
            this.controlPanelView.resetStats();

            // 连接 WebSocket
            if (!this.wsManager.connected) {
                this.controlPanelView.showStatus('正在连接...', 'info');
                await this.wsManager.connect();
            }

            // 获取max_ticks值
            const speed = parseFloat(this.controlPanelView.elements.speedSlider.value);
            const maxTicksInput = this.controlPanelView.elements.maxTicksInput;
            const maxTicks = maxTicksInput && maxTicksInput.value ? parseInt(maxTicksInput.value) : null;

            // 启动模拟
            this.wsManager.startSimulation(algorithm.name, scenario.name, speed, maxTicks);

            // 更新状态
            this.isSimulating = true;
            this.controlPanelView.setSimulationState(true);
            this.visualizationView.startAnimation();

            this.controlPanelView.showStatus('正在启动模拟...', 'info');

        } catch (error) {
            console.error('[SimulationController] Failed to start simulation:', error);
            this.controlPanelView.showStatus(`启动失败: ${error.message}`, 'error');
        }
    }

    /**
     * 处理暂停模拟
     * @private
     */
    _handlePauseSimulation() {
        this.wsManager.pauseSimulation();
        this.controlPanelView.setPauseState(true);
        this.controlPanelView.showStatus('模拟已暂停', 'info');
    }

    /**
     * 处理恢复模拟
     * @private
     */
    _handleResumeSimulation() {
        this.wsManager.resumeSimulation();
        this.controlPanelView.setPauseState(false);
        this.controlPanelView.showStatus('模拟继续运行', 'info');
    }

    /**
     * 处理停止模拟
     * @private
     */
    _handleStopSimulation() {
        this.wsManager.stopSimulation();
        this.visualizationView.stopAnimation();
        this.isSimulating = false;
        this.controlPanelView.setSimulationState(false);
        this.controlPanelView.showStatus('模拟已停止', 'info');
    }

    /**
     * 处理速度变化
     * @private
     */
    _handleSpeedChange(speed) {
        if (this.isSimulating) {
            this.wsManager.setSpeed(speed);
        }
    }

    /**
     * 更新算法显示
     * @private
     */
    _updateAlgorithmDisplay() {
        const algorithm = this.algorithmModel.getSelectedAlgorithm();
        if (algorithm) {
            this.controlPanelView.showAlgorithmDescription(algorithm);
        }
    }

    /**
     * 更新场景显示
     * @private
     */
    _updateScenarioDisplay() {
        const scenario = this.scenarioModel.getSelectedScenario();
        if (scenario) {
            this.controlPanelView.showScenarioInfo(scenario);
        }
    }
}
