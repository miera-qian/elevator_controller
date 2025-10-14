/**
 * 场景数据模型
 * 职责：封装场景数据和相关操作
 */
class ScenarioModel {
    constructor() {
        this.scenarios = [];
        this.selectedScenario = null;
    }

    /**
     * 从服务器加载场景列表
     * @returns {Promise<Array>} 场景列表
     */
    async loadScenarios() {
        try {
            const response = await fetch('/api/scenarios');
            const data = await response.json();
            this.scenarios = data.scenarios;

            // 默认选择第一个
            if (this.scenarios.length > 0) {
                this.selectedScenario = this.scenarios[0];
            }

            return this.scenarios;
        } catch (error) {
            console.error('Failed to load scenarios:', error);
            throw error;
        }
    }

    /**
     * 选择场景
     * @param {string} scenarioName - 场景名称
     * @returns {boolean} 是否成功
     */
    selectScenario(scenarioName) {
        const scenario = this.scenarios.find(s => s.name === scenarioName);
        if (scenario) {
            this.selectedScenario = scenario;
            return true;
        }
        return false;
    }

    /**
     * 获取当前选中的场景
     * @returns {Object|null} 场景信息
     */
    getSelectedScenario() {
        return this.selectedScenario;
    }

    /**
     * 获取所有场景
     * @returns {Array} 场景列表
     */
    getAllScenarios() {
        return this.scenarios;
    }
}
