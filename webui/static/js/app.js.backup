/**
 * Main Application
 * Coordinates UI, WebSocket, and Rendering
 */

// Global instances
let wsManager = null;
let renderer = null;
let animationFrameId = null;

// State
let algorithms = [];
let scenarios = [];
let isSimulating = false;

// DOM Elements
const elements = {
    algorithmSelect: null,
    algorithmDescription: null,
    scenarioSelect: null,
    scenarioInfo: null,
    speedSlider: null,
    speedValue: null,
    startBtn: null,
    pauseBtn: null,
    resumeBtn: null,
    stopBtn: null,
    statusMessage: null,
    stats: {}
};

// Initialize application
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Initializing application...');

    // Get DOM elements
    elements.algorithmSelect = document.getElementById('algorithm-select');
    elements.algorithmDescription = document.getElementById('algorithm-description');
    elements.scenarioSelect = document.getElementById('scenario-select');
    elements.scenarioInfo = document.getElementById('scenario-info');
    elements.speedSlider = document.getElementById('speed-slider');
    elements.speedValue = document.getElementById('speed-value');
    elements.startBtn = document.getElementById('start-btn');
    elements.pauseBtn = document.getElementById('pause-btn');
    elements.resumeBtn = document.getElementById('resume-btn');
    elements.stopBtn = document.getElementById('stop-btn');
    elements.statusMessage = document.getElementById('status-message');

    // Get stat elements
    elements.stats.tick = document.getElementById('stat-tick');
    elements.stats.total = document.getElementById('stat-total');
    elements.stats.waiting = document.getElementById('stat-waiting');
    elements.stats.inElevator = document.getElementById('stat-in-elevator');
    elements.stats.completed = document.getElementById('stat-completed');
    elements.stats.avgWait = document.getElementById('stat-avg-wait');

    console.log('Creating renderer...');
    // Initialize renderer
    renderer = new ElevatorRenderer('elevator-canvas');
    console.log('Renderer created, canvas size:', renderer.canvas.width, 'x', renderer.canvas.height);

    // Load algorithms and scenarios
    await loadAlgorithms();
    await loadScenarios();

    // Load default configuration into visualization
    if (scenarios.length > 0) {
        const defaultScenario = scenarios[0];
        console.log('Loading default scenario:', defaultScenario.name);
        const config = {
            floors: defaultScenario.floors,
            elevators: defaultScenario.elevators,
            capacity: defaultScenario.capacity || 8
        };
        renderer.initialize(config);
        console.log('Default configuration loaded:', config);
    }

    // Setup event listeners
    setupEventListeners();

    // Initialize WebSocket manager
    wsManager = new WebSocketManager();
    setupWebSocketHandlers();

    console.log('Application initialized');
    showStatus('应用已就绪，请选择算法和场景后点击"开始模拟"', 'info');
});

// Load available algorithms from API
async function loadAlgorithms() {
    try {
        const response = await fetch('/api/algorithms');
        const data = await response.json();
        algorithms = data.algorithms;

        // Populate select
        elements.algorithmSelect.innerHTML = '';
        algorithms.forEach(algo => {
            const option = document.createElement('option');
            option.value = algo.name;
            option.textContent = algo.display_name;
            elements.algorithmSelect.appendChild(option);
        });

        // Update description for first algorithm
        updateAlgorithmDescription();
    } catch (error) {
        console.error('Failed to load algorithms:', error);
        showStatus('加载算法列表失败', 'error');
    }
}

// Load available scenarios from API
async function loadScenarios() {
    try {
        const response = await fetch('/api/scenarios');
        const data = await response.json();
        scenarios = data.scenarios;

        // Populate select
        elements.scenarioSelect.innerHTML = '';
        scenarios.forEach(scenario => {
            const option = document.createElement('option');
            option.value = scenario.name;
            option.textContent = scenario.display_name;
            elements.scenarioSelect.appendChild(option);
        });

        // Update info for first scenario
        updateScenarioInfo();
    } catch (error) {
        console.error('Failed to load scenarios:', error);
        showStatus('加载场景列表失败', 'error');
    }
}

// Update algorithm description
function updateAlgorithmDescription() {
    const selected = elements.algorithmSelect.value;
    const algo = algorithms.find(a => a.name === selected);

    if (algo) {
        elements.algorithmDescription.innerHTML = `
            <strong>${algo.type}</strong><br>
            ${algo.description}
        `;
    }
}

// Update scenario info
function updateScenarioInfo() {
    const selected = elements.scenarioSelect.value;
    const scenario = scenarios.find(s => s.name === selected);

    if (scenario) {
        elements.scenarioInfo.innerHTML = `
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

        // Update visualization immediately when scenario changes
        const config = {
            floors: scenario.floors,
            elevators: scenario.elevators,
            capacity: scenario.capacity || 8
        };
        renderer.initialize(config);
        console.log('Scenario changed, visualization updated:', config);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Algorithm selection change
    elements.algorithmSelect.addEventListener('change', updateAlgorithmDescription);

    // Scenario selection change
    elements.scenarioSelect.addEventListener('change', updateScenarioInfo);

    // Speed slider
    elements.speedSlider.addEventListener('input', (e) => {
        const speed = parseFloat(e.target.value);
        elements.speedValue.textContent = `${speed.toFixed(1)}x`;

        // Update speed if simulation is running
        if (isSimulating && wsManager) {
            wsManager.setSpeed(speed);
        }
    });

    // Start button
    elements.startBtn.addEventListener('click', async () => {
        await startSimulation();
    });

    // Pause button
    elements.pauseBtn.addEventListener('click', () => {
        if (wsManager) {
            wsManager.pauseSimulation();
            elements.pauseBtn.disabled = true;
            elements.resumeBtn.disabled = false;
            showStatus('模拟已暂停', 'info');
        }
    });

    // Resume button
    elements.resumeBtn.addEventListener('click', () => {
        if (wsManager) {
            wsManager.resumeSimulation();
            elements.pauseBtn.disabled = false;
            elements.resumeBtn.disabled = true;
            showStatus('模拟继续运行', 'info');
        }
    });

    // Stop button
    elements.stopBtn.addEventListener('click', () => {
        stopSimulation();
    });
}

// Setup WebSocket message handlers
function setupWebSocketHandlers() {
    wsManager.on('init', (message) => {
        console.log('Received init:', message);
        renderer.initialize(message.building);
        showStatus(`模拟已启动: ${message.algorithm}`, 'success');
    });

    wsManager.on('state_update', (message) => {
        // Update renderer
        renderer.updateState(message);

        // Update stats
        updateStats(message);
    });

    wsManager.on('complete', (message) => {
        console.log('Simulation complete:', message);
        // Update renderer to show completion state (elevators return to floor 1)
        renderer.updateState(message);
        showStatus('模拟已完成', 'success');
        stopSimulation();
    });
}

// Start simulation
async function startSimulation() {
    const algorithm = elements.algorithmSelect.value;
    const scenario = elements.scenarioSelect.value;
    const speed = parseFloat(elements.speedSlider.value);

    if (!algorithm || !scenario) {
        showStatus('请选择算法和场景', 'error');
        return;
    }

    try {
        // Connect WebSocket if not connected
        if (!wsManager.connected) {
            showStatus('正在连接...', 'info');
            await wsManager.connect();
        }

        // Start simulation
        wsManager.startSimulation(algorithm, scenario, speed);

        // Update UI state
        isSimulating = true;
        elements.startBtn.disabled = true;
        elements.pauseBtn.disabled = false;
        elements.stopBtn.disabled = false;
        elements.algorithmSelect.disabled = true;
        elements.scenarioSelect.disabled = true;

        // Start animation loop
        startAnimationLoop();

        showStatus('正在启动模拟...', 'info');
    } catch (error) {
        console.error('Failed to start simulation:', error);
        showStatus('启动模拟失败: ' + error.message, 'error');
    }
}

// Stop simulation
function stopSimulation() {
    if (wsManager) {
        wsManager.stopSimulation();
    }

    // Stop animation
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
    }

    // Update UI state
    isSimulating = false;
    elements.startBtn.disabled = false;
    elements.pauseBtn.disabled = true;
    elements.resumeBtn.disabled = true;
    elements.stopBtn.disabled = true;
    elements.algorithmSelect.disabled = false;
    elements.scenarioSelect.disabled = false;

    showStatus('模拟已停止', 'info');
}

// Animation loop
function startAnimationLoop() {
    function animate() {
        if (!isSimulating) return;

        // Animate renderer
        renderer.animate();

        // Continue loop
        animationFrameId = requestAnimationFrame(animate);
    }

    animate();
}

// Update statistics display
function updateStats(message) {
    if (message.tick !== undefined) {
        elements.stats.tick.textContent = message.tick;
    }

    if (message.stats) {
        const stats = message.stats;

        if (stats.total_passengers !== undefined) {
            elements.stats.total.textContent = stats.total_passengers;
        }
        if (stats.waiting !== undefined) {
            elements.stats.waiting.textContent = stats.waiting;
        }
        if (stats.in_elevator !== undefined) {
            elements.stats.inElevator.textContent = stats.in_elevator;
        }
        if (stats.completed !== undefined) {
            elements.stats.completed.textContent = stats.completed;
        }
        if (stats.avg_wait_time !== undefined) {
            elements.stats.avgWait.textContent = stats.avg_wait_time.toFixed(2);
        }
    }
}

// Show status message
function showStatus(message, type = 'info') {
    elements.statusMessage.textContent = message;
    elements.statusMessage.className = `status-message ${type}`;

    // Auto-hide after 5 seconds for non-error messages
    if (type !== 'error') {
        setTimeout(() => {
            elements.statusMessage.className = 'status-message';
        }, 5000);
    }
}
