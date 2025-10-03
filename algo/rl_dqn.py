#!/usr/bin/env python3
"""
Reinforcement Learning Based Elevator Algorithm (Q-Learning)

Uses Q-learning to learn optimal elevator scheduling policy through experience.
The agent learns to minimize passenger wait times by trial and error.
"""

import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, deque
import random

from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from .base_algorithm import BaseAlgorithm


class QLearningAgent:
    """
    Q-Learning Agent for elevator scheduling.

    Uses tabular Q-learning to learn state-action values.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        epsilon: float = 0.2,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.01
    ):
        """
        Initialize Q-learning agent.

        Args:
            learning_rate: Learning rate (alpha)
            discount_factor: Discount factor for future rewards (gamma)
            epsilon: Exploration rate for epsilon-greedy policy
            epsilon_decay: Decay rate for epsilon
            epsilon_min: Minimum epsilon value
        """
        self.q_table: Dict[Tuple, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min

        # Experience replay buffer
        self.experience_buffer = deque(maxlen=10000)

        # Statistics
        self.total_rewards = 0
        self.episode_count = 0

    def get_action(self, state: Tuple, available_actions: List[int]) -> int:
        """
        Select action using epsilon-greedy policy.

        Args:
            state: Current state tuple
            available_actions: List of available action indices

        Returns:
            Selected action index
        """
        if not available_actions:
            return 0

        # Epsilon-greedy exploration
        if random.random() < self.epsilon:
            return random.choice(available_actions)

        # Exploitation: choose best known action
        q_values = self.q_table[state]
        best_action = max(available_actions, key=lambda a: q_values[a])
        return best_action

    def update(self, state: Tuple, action: int, reward: float, next_state: Tuple, done: bool):
        """
        Update Q-value using Q-learning update rule.

        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Whether episode is done
        """
        # Store experience
        self.experience_buffer.append((state, action, reward, next_state, done))

        # Q-learning update
        current_q = self.q_table[state][action]

        if done:
            target_q = reward
        else:
            # Get max Q-value for next state
            next_q_values = self.q_table[next_state]
            max_next_q = max(next_q_values.values()) if next_q_values else 0.0
            target_q = reward + self.discount_factor * max_next_q

        # Update Q-value
        self.q_table[state][action] = current_q + self.learning_rate * (target_q - current_q)

        # Update statistics
        self.total_rewards += reward

    def decay_epsilon(self):
        """Decay exploration rate"""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def save(self, filepath: str):
        """Save Q-table to file"""
        with open(filepath, 'wb') as f:
            pickle.dump({
                'q_table': dict(self.q_table),
                'epsilon': self.epsilon,
                'total_rewards': self.total_rewards,
                'episode_count': self.episode_count
            }, f)

    def load(self, filepath: str):
        """Load Q-table from file"""
        if Path(filepath).exists():
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
                self.q_table = defaultdict(lambda: defaultdict(float), data['q_table'])
                self.epsilon = data.get('epsilon', self.epsilon)
                self.total_rewards = data.get('total_rewards', 0)
                self.episode_count = data.get('episode_count', 0)
            return True
        return False


class RLDQNAlgorithm(BaseAlgorithm):
    """
    Reinforcement Learning based elevator scheduling algorithm.

    Uses Q-learning to learn optimal elevator assignment policy.
    The agent learns from experience to minimize passenger wait times.

    State: Simplified building state (elevator positions, waiting passengers)
    Actions: Which elevator to assign to each new passenger call
    Reward: Negative of passenger wait time (encourages faster service)
    """

    def __init__(
        self,
        server_url: str = "http://127.0.0.1:8000",
        enable_logging: bool = True,
        model_path: str = "models/rl_elevator.pkl",
        training_mode: bool = True
    ):
        """
        Initialize RL algorithm.

        Args:
            server_url: Simulator server URL
            enable_logging: Enable debug logging
            model_path: Path to save/load Q-table
            training_mode: Whether to train (explore) or exploit learned policy
        """
        super().__init__(server_url, enable_logging)

        # RL agent
        self.agent = QLearningAgent(
            learning_rate=0.1,
            discount_factor=0.95,
            epsilon=0.2 if training_mode else 0.0  # No exploration in production
        )

        # Load pre-trained model if exists
        self.model_path = model_path
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
        if self.agent.load(model_path):
            print(f"Loaded pre-trained model from {model_path}")

        self.training_mode = training_mode

        # State tracking for RL
        self.last_state: Optional[Tuple] = None
        self.last_action: Optional[int] = None
        self.passenger_call_times: Dict[int, int] = {}  # passenger_id -> call_tick
        self.current_tick = 0

    def _get_state(self) -> Tuple:
        """
        Extract state representation from current environment.

        State includes:
        - Number of waiting passengers per floor (discretized)
        - Elevator positions (discretized)
        - Elevator load factors (discretized)

        Returns:
            State tuple for Q-table lookup
        """
        # Discretize waiting passengers (0: none, 1: few, 2: many)
        waiting_state = []
        for floor_num in range(self.num_floors):
            total_waiting = len(self.waiting_up[floor_num]) + len(self.waiting_down[floor_num])
            if total_waiting == 0:
                waiting_state.append(0)
            elif total_waiting <= 2:
                waiting_state.append(1)
            else:
                waiting_state.append(2)

        # Discretize elevator states
        elevator_state = []
        for elevator in self.elevators:
            # Position (discretized to thirds)
            pos_discrete = int(elevator.current_floor / self.num_floors * 3)
            # Load (discretized: 0=empty, 1=partial, 2=full)
            load_discrete = 0 if elevator.load_factor < 0.3 else (1 if elevator.load_factor < 0.7 else 2)
            elevator_state.append((pos_discrete, load_discrete))

        return tuple(waiting_state + [e for pair in elevator_state for e in pair])

    def _get_reward(self, passenger_id: int) -> float:
        """
        Calculate reward for passenger boarding.

        Reward is negative of wait time (encourages faster service).

        Args:
            passenger_id: ID of passenger who boarded

        Returns:
            Reward value
        """
        if passenger_id in self.passenger_call_times:
            wait_time = self.current_tick - self.passenger_call_times[passenger_id]
            # Negative reward proportional to wait time
            reward = -wait_time / 10.0  # Scale down
            del self.passenger_call_times[passenger_id]
            return reward
        return 0.0

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """Handle new passenger call using RL policy"""
        floor_num = floor.floor
        passenger_id = passenger.id

        # Track waiting passenger
        if direction == "up":
            self.waiting_up[floor_num].add(passenger_id)
        else:
            self.waiting_down[floor_num].add(passenger_id)

        # Record call time for reward calculation
        self.passenger_call_times[passenger_id] = self.current_tick

        # Get current state
        current_state = self._get_state()

        # Get available actions (elevator indices)
        available_actions = list(range(self.num_elevators))

        # Select elevator using RL policy
        elevator_idx = self.agent.get_action(current_state, available_actions)

        # Assign selected elevator
        selected_elevator = self.elevators[elevator_idx]
        selected_elevator.go_to_floor(floor_num)
        if floor_num not in self.elevator_targets[selected_elevator.id]:
            self.elevator_targets[selected_elevator.id].append(floor_num)

        # Store state-action for learning
        self.last_state = current_state
        self.last_action = elevator_idx

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """Handle idle elevator - use nearest waiting passenger"""
        # Simple heuristic for idle elevators
        best_floor = self._find_nearest_waiting_call(elevator.current_floor)

        if best_floor is not None:
            elevator.go_to_floor(best_floor)
            if best_floor not in self.elevator_targets[elevator.id]:
                self.elevator_targets[elevator.id].append(best_floor)

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """Decide whether to stop at approaching floor"""
        floor_num = floor.floor

        # Stop if passengers waiting in same direction
        if direction == "up" and self.waiting_up[floor_num]:
            elevator.go_to_floor(floor_num)
        elif direction == "down" and self.waiting_down[floor_num]:
            elevator.go_to_floor(floor_num)

        # Handle boundary conditions
        if floor_num == self.num_floors - 1 and self.waiting_down[floor_num]:
            elevator.go_to_floor(floor_num)
        elif floor_num == 0 and self.waiting_up[floor_num]:
            elevator.go_to_floor(floor_num)

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """Handle elevator stopped"""
        floor_num = floor.floor

        if floor_num in self.elevator_targets[elevator.id]:
            self.elevator_targets[elevator.id].remove(floor_num)

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """Handle passenger boarding - update RL agent with reward"""
        floor_num = passenger.origin_floor
        passenger_id = passenger.id
        destination = passenger.destination_floor

        # Remove from waiting lists
        self.waiting_up[floor_num].discard(passenger_id)
        self.waiting_down[floor_num].discard(passenger_id)

        # Register destination
        elevator.go_to_floor(destination)
        if destination not in self.elevator_targets[elevator.id]:
            self.elevator_targets[elevator.id].append(destination)

        # RL update: calculate reward and update Q-table
        if self.training_mode and self.last_state is not None:
            reward = self._get_reward(passenger_id)
            next_state = self._get_state()

            self.agent.update(
                state=self.last_state,
                action=self.last_action,
                reward=reward,
                next_state=next_state,
                done=False
            )

    def on_event_execute_start(self, tick, events, elevators, floors):
        """Track current tick for reward calculation"""
        self.current_tick = tick

    def _find_nearest_waiting_call(self, current_floor: int) -> Optional[int]:
        """Find nearest floor with waiting passengers"""
        min_distance = float('inf')
        best_floor = None

        for floor_num in range(self.num_floors):
            if self.waiting_up[floor_num] or self.waiting_down[floor_num]:
                distance = abs(current_floor - floor_num)
                if distance < min_distance:
                    min_distance = distance
                    best_floor = floor_num

        return best_floor

    def save_model(self):
        """Save learned Q-table"""
        self.agent.save(self.model_path)
        print(f"Model saved to {self.model_path}")

    def __del__(self):
        """Save model on cleanup if in training mode"""
        if self.training_mode:
            try:
                self.save_model()
            except:
                pass
