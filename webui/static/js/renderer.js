/**
 * Elevator Canvas Renderer
 * Handles all visualization rendering on the canvas
 */

class ElevatorRenderer {
    constructor(canvasId) {
        console.log('ElevatorRenderer: Initializing with canvas ID:', canvasId);
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error('Canvas element not found:', canvasId);
            return;
        }
        this.ctx = this.canvas.getContext('2d');
        console.log('ElevatorRenderer: Canvas context created');

        // Building configuration
        this.numFloors = 10;
        this.numElevators = 3;
        this.capacity = 8;

        // Layout dimensions (will be calculated based on canvas size)
        this.floorHeight = 60;
        this.elevatorWidth = 80;
        this.elevatorHeight = 50;
        this.elevatorSpacing = 100;
        this.leftMargin = 100;
        this.rightMargin = 200; // Space for waiting area
        this.topMargin = 50;
        this.bottomMargin = 50;

        // Animation state
        this.elevatorPositions = []; // Current visual positions for smooth animation
        this.targetPositions = []; // Target positions from server state

        // State tracking (no boarding animation)
        this.previousState = null;

        // Current state (initialized with empty data)
        this.currentState = null;

        // Simulation complete flag
        this.simulationComplete = false;

        // Passengers
        this.passengerRadius = 8; // Increased from 6 for better visibility

        // Colors
        this.colors = {
            background: '#ffffff',
            floor: '#34495e',
            floorLine: '#bdc3c7',
            elevator: '#3498db',
            elevatorIdle: '#95a5a6',
            elevatorUp: '#27ae60',
            elevatorDown: '#e67e22',
            passenger: '#e74c3c',
            passengerInElevator: '#f39c12',
            text: '#2c3e50',
            textLight: '#7f8c8d'
        };

        // Initialize with default state for initial rendering
        this.currentState = {
            elevators: [],
            waiting: {}
        };

        // Initialize
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
    }

    resizeCanvas() {
        const container = this.canvas.parentElement;
        const rect = container.getBoundingClientRect();

        // Set canvas size (leave some padding)
        this.canvas.width = rect.width - 40;
        this.canvas.height = rect.height - 40;

        // Recalculate layout based on canvas size
        this.calculateLayout();

        // Redraw
        this.render();
    }

    calculateLayout() {
        const availableHeight = this.canvas.height - this.topMargin - this.bottomMargin;

        // Calculate floor height based on number of floors
        this.floorHeight = Math.min(60, availableHeight / (this.numFloors + 1));

        // Calculate elevator spacing to fit exactly
        // Each elevator needs: elevatorWidth + some spacing
        // Total width = numElevators * elevatorSpacing
        if (this.numElevators > 0) {
            this.elevatorSpacing = 100; // Fixed spacing for consistent layout

            // Calculate the total width needed for all elevators
            this.elevatorAreaWidth = this.numElevators * this.elevatorSpacing;

            // Left-align the elevator area
            this.elevatorAreaStartX = this.leftMargin;
            this.elevatorAreaEndX = this.leftMargin + this.elevatorAreaWidth;
        }
    }

    initialize(config) {
        console.log('ElevatorRenderer: Initializing with config:', config);
        this.numFloors = config.floors || 10;
        this.numElevators = config.elevators || 3;
        this.capacity = config.capacity || 8;

        // Reset simulation complete flag
        this.simulationComplete = false;

        // Initialize elevator visual positions at floor 1
        this.elevatorPositions = [];
        this.targetPositions = [];
        for (let i = 0; i < this.numElevators; i++) {
            this.elevatorPositions.push(1); // Start at floor 1
            this.targetPositions.push(1);
        }

        // IMPROVEMENT #1: 数据集选择完成后所有电梯均应当立刻被渲染出来
        // Initialize current state with default elevator data at floor 1
        this.currentState = {
            elevators: Array.from({ length: this.numElevators }, (_, i) => ({
                id: i,
                floor: 1,
                direction: 'idle',
                passengers: [],
                capacity: this.capacity
            })),
            waiting: {}
        };

        console.log('ElevatorRenderer: State initialized, elevators:', this.currentState.elevators.length);

        this.calculateLayout();
        this.render(); // This will show elevators immediately
        console.log('ElevatorRenderer: Initial render complete');
    }

    updateState(state) {
        // Check for simulation completion
        if (state.type === 'complete') {
            this.simulationComplete = true;
            // IMPROVEMENT #4: 整个调度结束后所有电梯回到最底层
            // Force all elevators to floor 1 immediately (no animation)
            for (let i = 0; i < this.numElevators; i++) {
                this.elevatorPositions[i] = 1;  // Current visual position
                this.targetPositions[i] = 1;     // Target position
            }

            // Clear all passengers from elevators and waiting areas
            // Create clean state with empty elevators at floor 1
            this.currentState = {
                elevators: Array.from({ length: this.numElevators }, (_, i) => ({
                    id: i,
                    floor: 1,
                    direction: 'idle',
                    passengers: [],
                    capacity: this.capacity
                })),
                waiting: {}
            };

            // Force immediate render to show completion state
            this.render();
            return; // Don't update state further for complete message
        } else {
            // Update target positions for elevators
            if (state.elevators) {
                console.log('[Renderer] Updating elevator targets:', state.elevators);
                state.elevators.forEach((elevator, idx) => {
                    if (idx < this.targetPositions.length) {
                        console.log(`[Renderer] E${idx}: current=${this.elevatorPositions[idx]}, target=${elevator.floor}, direction=${elevator.direction}`);
                        this.targetPositions[idx] = elevator.floor;
                    }
                });
            }

            // IMPROVEMENT #5: Boarding state detection removed - simple display only
        }

        // Store previous state before updating current
        this.previousState = this.currentState;

        // Store state for rendering
        this.currentState = state;
    }


    animate() {
        // Smoothly interpolate elevator positions towards targets
        let needsUpdate = false;

        for (let i = 0; i < this.elevatorPositions.length; i++) {
            const current = this.elevatorPositions[i];
            const target = this.targetPositions[i];
            const diff = target - current;

            if (Math.abs(diff) > 0.01) {
                // Smooth interpolation (20% each frame)
                this.elevatorPositions[i] = current + diff * 0.2;
                needsUpdate = true;
            } else {
                this.elevatorPositions[i] = target;
            }
        }

        this.render();
        return needsUpdate;
    }

    render() {
        // Clear canvas
        this.ctx.fillStyle = this.colors.background;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw floors
        this.drawFloors();

        // Draw elevators
        this.drawElevators();

        // Draw waiting passengers
        this.drawWaitingPassengers();
    }

    drawFloors() {
        const startY = this.canvas.height - this.bottomMargin;

        for (let floor = 1; floor <= this.numFloors; floor++) {
            const y = startY - (floor - 1) * this.floorHeight;

            // Floor line - only covers elevator area
            this.ctx.strokeStyle = this.colors.floorLine;
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            this.ctx.moveTo(this.elevatorAreaStartX, y);
            this.ctx.lineTo(this.elevatorAreaEndX, y);
            this.ctx.stroke();

            // Floor number on the left
            this.ctx.fillStyle = this.colors.text;
            this.ctx.font = 'bold 14px sans-serif';
            this.ctx.textAlign = 'right';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText(`F${floor}`, this.elevatorAreaStartX - 20, y);
        }

        // Draw elevator column labels at the bottom
        this.drawElevatorLabels();
    }

    drawElevatorLabels() {
        const startY = this.canvas.height - this.bottomMargin;
        const labelY = startY + 25; // Below the bottom floor line

        this.ctx.fillStyle = this.colors.text;
        this.ctx.font = 'bold 12px sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'top';

        for (let i = 0; i < this.numElevators; i++) {
            const x = this.elevatorAreaStartX + i * this.elevatorSpacing + this.elevatorSpacing / 2;
            this.ctx.fillText(`E${i}`, x, labelY);
        }
    }

    drawElevators() {
        if (!this.currentState || !this.currentState.elevators) {
            return;
        }

        const startY = this.canvas.height - this.bottomMargin;

        this.currentState.elevators.forEach((elevator, idx) => {
            if (idx >= this.elevatorPositions.length) return;

            const visualFloor = this.elevatorPositions[idx];
            // Position elevators in their designated columns
            const x = this.elevatorAreaStartX + idx * this.elevatorSpacing + this.elevatorSpacing / 2;

            // IMPROVEMENT #3: 电梯应该停泊在表示楼层的两根线之间
            // Position elevator centered between two floor lines
            const floorY = startY - (visualFloor - 1) * this.floorHeight;
            const y = floorY - this.floorHeight / 2;

            // Determine elevator color based on direction
            let elevatorColor = this.colors.elevatorIdle;
            console.log(`[Renderer] E${idx} direction: "${elevator.direction}", color will be: ${elevatorColor}`);
            if (elevator.direction === 'up') {
                elevatorColor = this.colors.elevatorUp;
                console.log(`[Renderer] E${idx} -> UP color: ${elevatorColor}`);
            } else if (elevator.direction === 'down') {
                elevatorColor = this.colors.elevatorDown;
                console.log(`[Renderer] E${idx} -> DOWN color: ${elevatorColor}`);
            }

            // Draw elevator box
            this.ctx.fillStyle = elevatorColor;
            this.ctx.fillRect(
                x - this.elevatorWidth / 2,
                y - this.elevatorHeight / 2,
                this.elevatorWidth,
                this.elevatorHeight
            );

            // Draw elevator border
            this.ctx.strokeStyle = this.colors.floor;
            this.ctx.lineWidth = 2;
            this.ctx.strokeRect(
                x - this.elevatorWidth / 2,
                y - this.elevatorHeight / 2,
                this.elevatorWidth,
                this.elevatorHeight
            );

            // Draw elevator ID
            this.ctx.fillStyle = '#ffffff';
            this.ctx.font = 'bold 12px sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'top';
            this.ctx.fillText(`E${elevator.id}`, x, y - this.elevatorHeight / 2 + 5);

            // Draw passenger count
            const passengerCount = elevator.passengers ? elevator.passengers.length : 0;
            this.ctx.fillStyle = '#ffffff';
            this.ctx.font = '14px sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText(`${passengerCount}/${this.capacity}`, x, y + 8);

            // Draw direction arrow
            if (elevator.direction !== 'idle') {
                this.drawArrow(
                    x,
                    y - this.elevatorHeight / 2 - 10,
                    elevator.direction === 'up'
                );
            }

            // IMPROVEMENT #2 & #5: 电梯中表示乘客的圆圈应该与等候区一致，获得一个唯一的编号显示在圆圈上
            // Draw passengers inside elevator with their IDs
            this.drawPassengersInElevator(x, y, elevator.passengers || []);
        });
    }

    drawArrow(x, y, pointUp) {
        this.ctx.fillStyle = this.colors.text;
        this.ctx.beginPath();

        if (pointUp) {
            this.ctx.moveTo(x, y - 8);
            this.ctx.lineTo(x - 6, y);
            this.ctx.lineTo(x + 6, y);
        } else {
            this.ctx.moveTo(x, y + 8);
            this.ctx.lineTo(x - 6, y);
            this.ctx.lineTo(x + 6, y);
        }

        this.ctx.closePath();
        this.ctx.fill();
    }

    drawPassengersInElevator(elevatorX, elevatorY, passengers) {
        // IMPROVEMENT #2: 电梯中表示乘客的圆圈应该与等候区一致，获得一个唯一的编号显示在圆圈上
        // Draw circles with passenger IDs (same style as waiting area)

        const maxPerRow = 4;
        const spacing = 16; // Increased spacing for larger circles

        passengers.forEach((passenger, idx) => {
            const row = Math.floor(idx / maxPerRow);
            const col = idx % maxPerRow;

            const x = elevatorX - (maxPerRow - 1) * spacing / 2 + col * spacing;
            const y = elevatorY - 8 + row * spacing;

            // Draw passenger circle (same size as waiting area)
            this.ctx.fillStyle = this.colors.passengerInElevator;
            this.ctx.beginPath();
            this.ctx.arc(x, y, this.passengerRadius, 0, Math.PI * 2);
            this.ctx.fill();

            // Draw passenger ID (use passenger.id if available, otherwise use index)
            const passengerId = passenger.id || idx;
            this.ctx.fillStyle = '#ffffff';
            this.ctx.font = 'bold 10px sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText(passengerId, x, y);
        });
    }

    drawWaitingPassengers() {
        if (!this.currentState || !this.currentState.waiting) {
            return;
        }

        const startY = this.canvas.height - this.bottomMargin;
        // Position waiting area to the right of elevator area
        const waitingAreaX = this.elevatorAreaEndX + 20;

        // Draw waiting area for each floor
        Object.entries(this.currentState.waiting).forEach(([floorStr, passengers]) => {
            const floor = parseInt(floorStr);
            const floorY = startY - (floor - 1) * this.floorHeight;

            if (passengers && passengers.length > 0) {
                // Draw passengers waiting at this floor
                const maxPerRow = 8;
                const spacing = 18; // Increased spacing for larger circles

                passengers.forEach((passenger, idx) => {
                    const row = Math.floor(idx / maxPerRow);
                    const col = idx % maxPerRow;

                    const x = waitingAreaX + col * spacing;
                    const py = floorY - 25 - row * spacing; // Adjusted to be between floors

                    // IMPROVEMENT #2: Draw passenger circle with unique ID
                    this.ctx.fillStyle = this.colors.passenger;
                    this.ctx.beginPath();
                    this.ctx.arc(x, py, this.passengerRadius, 0, Math.PI * 2);
                    this.ctx.fill();

                    // Draw passenger ID (unique identifier)
                    const passengerId = passenger.id || idx;
                    this.ctx.fillStyle = '#ffffff';
                    this.ctx.font = 'bold 10px sans-serif';
                    this.ctx.textAlign = 'center';
                    this.ctx.textBaseline = 'middle';
                    this.ctx.fillText(passengerId, x, py);
                });

                // Draw count label (showing actual waiting count)
                this.ctx.fillStyle = this.colors.text;
                this.ctx.font = '12px sans-serif';
                this.ctx.textAlign = 'left';
                this.ctx.textBaseline = 'middle';
                this.ctx.fillText(`等待: ${passengers.length}`, waitingAreaX, floorY + 15);
            }
        });
    }

}
