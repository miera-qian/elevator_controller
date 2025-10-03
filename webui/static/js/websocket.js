/**
 * WebSocket Manager
 * Handles WebSocket connection and message handling
 */

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.messageHandlers = {};
    }

    connect() {
        return new Promise((resolve, reject) => {
            // Determine WebSocket URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/simulation`;

            try {
                this.ws = new WebSocket(wsUrl);

                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.connected = true;
                    this.reconnectAttempts = 0;
                    resolve();
                };

                this.ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    this.connected = false;
                    this.handleDisconnect();
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    reject(error);
                };

                this.ws.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        this.handleMessage(message);
                    } catch (error) {
                        console.error('Failed to parse message:', error);
                    }
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
            this.connected = false;
        }
    }

    send(message) {
        if (this.connected && this.ws) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.error('WebSocket not connected');
        }
    }

    on(messageType, handler) {
        if (!this.messageHandlers[messageType]) {
            this.messageHandlers[messageType] = [];
        }
        this.messageHandlers[messageType].push(handler);
    }

    off(messageType, handler) {
        if (this.messageHandlers[messageType]) {
            this.messageHandlers[messageType] = this.messageHandlers[messageType].filter(
                h => h !== handler
            );
        }
    }

    handleMessage(message) {
        const handlers = this.messageHandlers[message.type];
        if (handlers) {
            handlers.forEach(handler => {
                try {
                    handler(message);
                } catch (error) {
                    console.error('Error in message handler:', error);
                }
            });
        }
    }

    handleDisconnect() {
        // Attempt to reconnect
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);

            setTimeout(() => {
                this.connect().catch(error => {
                    console.error('Reconnect failed:', error);
                });
            }, 1000 * this.reconnectAttempts);
        } else {
            console.error('Max reconnect attempts reached');
        }
    }

    // Simulation control methods
    startSimulation(algorithm, scenario, speed = 1.0) {
        this.send({
            type: 'start',
            algorithm: algorithm,
            scenario: scenario,
            speed: speed
        });
    }

    pauseSimulation() {
        this.send({
            type: 'pause'
        });
    }

    resumeSimulation() {
        this.send({
            type: 'resume'
        });
    }

    stopSimulation() {
        this.send({
            type: 'stop'
        });
    }

    setSpeed(speed) {
        this.send({
            type: 'set_speed',
            speed: speed
        });
    }
}
