/**
 * Main Application Entry Point (MVC Architecture)
 * 职责：初始化和组装 MVC 组件
 */

document.addEventListener('DOMContentLoaded', async () => {
    console.log('[App] Initializing MVC architecture...');

    try {
        // Create Model instances
        const algorithmModel = new AlgorithmModel();
        const scenarioModel = new ScenarioModel();

        // Create View instances
        const controlPanelView = new ControlPanelView();
        const visualizationView = new VisualizationView('elevator-canvas');

        // Create Controller with dependency injection
        const simulationController = new SimulationController(
            algorithmModel,
            scenarioModel,
            controlPanelView,
            visualizationView
        );

        // Initialize application
        await simulationController.initialize();

        console.log('[App] Application initialized with MVC architecture');
    } catch (error) {
        console.error('[App] Initialization failed:', error);
        // Show error message to user
        const statusMessage = document.getElementById('status-message');
        if (statusMessage) {
            statusMessage.textContent = '应用初始化失败: ' + error.message;
            statusMessage.className = 'status-message error';
        }
    }
});
