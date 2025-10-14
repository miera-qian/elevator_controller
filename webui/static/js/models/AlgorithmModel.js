/**
 * 算法数据模型
 * 职责：封装算法数据和相关操作
 */
class AlgorithmModel {
    constructor() {
        this.algorithms = [];
        this.selectedAlgorithm = null;
    }

    /**
     * 从服务器加载算法列表
     * @returns {Promise<Array>} 算法列表
     */
    async loadAlgorithms() {
        try {
            const response = await fetch('/api/algorithms');
            const data = await response.json();
            this.algorithms = data.algorithms;

            // 默认选择第一个
            if (this.algorithms.length > 0) {
                this.selectedAlgorithm = this.algorithms[0];
            }

            return this.algorithms;
        } catch (error) {
            console.error('Failed to load algorithms:', error);
            throw error;
        }
    }

    /**
     * 选择算法
     * @param {string} algorithmName - 算法名称
     * @returns {boolean} 是否成功
     */
    selectAlgorithm(algorithmName) {
        const algorithm = this.algorithms.find(a => a.name === algorithmName);
        if (algorithm) {
            this.selectedAlgorithm = algorithm;
            return true;
        }
        return false;
    }

    /**
     * 获取当前选中的算法
     * @returns {Object|null} 算法信息
     */
    getSelectedAlgorithm() {
        return this.selectedAlgorithm;
    }

    /**
     * 获取所有算法
     * @returns {Array} 算法列表
     */
    getAllAlgorithms() {
        return this.algorithms;
    }
}
