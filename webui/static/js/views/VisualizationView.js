/**
 * 可视化视图
 * 职责：封装电梯可视化渲染器，提供统一接口
 */
class VisualizationView {
    constructor(canvasId) {
        // 使用现有的 ElevatorRenderer
        this.renderer = new ElevatorRenderer(canvasId);
        this.animationFrameId = null;
    }

    /**
     * 初始化可视化配置
     * @param {Object} config - 配置对象 {floors, elevators, capacity}
     */
    initialize(config) {
        console.log('VisualizationView: Initializing with config:', config);
        this.renderer.initialize(config);
    }

    /**
     * 更新状态
     * @param {Object} state - 状态数据
     */
    updateState(state) {
        this.renderer.updateState(state);
    }

    /**
     * 开始动画循环
     */
    startAnimation() {
        const animate = () => {
            this.renderer.animate();
            this.animationFrameId = requestAnimationFrame(animate);
        };
        animate();
    }

    /**
     * 停止动画循环
     */
    stopAnimation() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
    }

    /**
     * 处理模拟完成
     */
    handleCompletion() {
        // renderer.updateState 会处理 complete 消息
        this.stopAnimation();
    }
}
