#!/usr/bin/env python3
"""
Hybrid SCAN-RL Algorithm

Combines OptimizedScanAlgorithm with reinforcement learning for best of both worlds:
- Cold start: Uses reliable SCAN algorithm immediately
- Training: Continuously trains RL agent in background
- Transition: Switches to RL when performance threshold is met
- Fallback: Returns to SCAN if RL performance degrades

This approach provides:
1. Immediate good performance (SCAN)
2. Adaptive learning (RL)
3. Robustness (automatic fallback)
"""

import time
from typing import List, Optional
from collections import deque
from pathlib import Path

from elevator_saga.client.proxy_models import ProxyElevator, ProxyFloor, ProxyPassenger
from .base_algorithm import BaseAlgorithm
from .optimized_scan import OptimizedScanAlgorithm
from .rl_dqn import RLDQNAlgorithm


class PerformanceMonitor:
    """
    Monitor algorithm performance to decide when to switch from SCAN to RL.

    Tracks rolling average of wait times to assess RL readiness.
    """

    def __init__(self, window_size: int = 100, threshold_ratio: float = 0.85):
        """
        Initialize performance monitor.

        Args:
            window_size: Number of recent wait times to track
            threshold_ratio: RL must perform at least this ratio relative to SCAN
                           (e.g., 0.85 means RL wait time <= 0.85 * SCAN wait time)
        """
        self.window_size = window_size
        self.threshold_ratio = threshold_ratio

        # Track wait times for both algorithms
        self.scan_wait_times = deque(maxlen=window_size)
        self.rl_wait_times = deque(maxlen=window_size)

        # Track passenger boarding times for wait time calculation
        self.passenger_call_times = {}  # passenger_id -> call_time

        # Performance statistics
        self.scan_avg_wait = float('inf')
        self.rl_avg_wait = float('inf')
        self.samples_collected = 0

    def record_passenger_call(self, passenger_id: int, tick: int):
        """Record when passenger calls elevator"""
        self.passenger_call_times[passenger_id] = tick

    def record_passenger_board(self, passenger_id: int, tick: int, algorithm_type: str):
        """
        Record when passenger boards and calculate wait time.

        Args:
            passenger_id: Passenger ID
            tick: Current simulation tick
            algorithm_type: 'scan' or 'rl' - which algorithm handled this
        """
        if passenger_id not in self.passenger_call_times:
            return

        call_time = self.passenger_call_times[passenger_id]
        wait_time = tick - call_time

        # Record to appropriate buffer
        if algorithm_type == 'scan':
            self.scan_wait_times.append(wait_time)
            if len(self.scan_wait_times) >= 10:
                self.scan_avg_wait = sum(self.scan_wait_times) / len(self.scan_wait_times)
        elif algorithm_type == 'rl':
            self.rl_wait_times.append(wait_time)
            if len(self.rl_wait_times) >= 10:
                self.rl_avg_wait = sum(self.rl_wait_times) / len(self.rl_wait_times)

        self.samples_collected += 1

        # Clean up
        del self.passenger_call_times[passenger_id]

    def should_use_rl(self, min_samples: int = 50) -> bool:
        """
        Decide if RL is ready to be used.

        Criteria:
        1. Both algorithms have collected minimum samples
        2. RL average wait time <= threshold_ratio * SCAN average wait time

        Args:
            min_samples: Minimum samples needed before switching

        Returns:
            True if should switch to RL, False otherwise
        """
        # Need enough samples from both
        if len(self.scan_wait_times) < min_samples or len(self.rl_wait_times) < min_samples:
            return False

        # RL must perform better than threshold
        if self.rl_avg_wait <= self.scan_avg_wait * self.threshold_ratio:
            return True

        return False

    def get_performance_ratio(self) -> Optional[float]:
        """
        Get RL/SCAN performance ratio.

        Returns:
            Ratio (< 1.0 means RL is better), None if not enough data
        """
        if self.scan_avg_wait == float('inf') or self.rl_avg_wait == float('inf'):
            return None
        if self.scan_avg_wait == 0:
            return None
        return self.rl_avg_wait / self.scan_avg_wait


class HybridScanRLAlgorithm(BaseAlgorithm):
    """
    Hybrid algorithm that combines SCAN and RL for optimal performance.

    Strategy:
    1. Start with SCAN for immediate good performance
    2. Train RL agent in parallel during cold start phase
    3. Monitor both algorithms' performance
    4. Switch to RL when it demonstrates superior performance
    5. Keep monitoring and fallback to SCAN if RL degrades

    This provides:
    - No cold start penalty (SCAN is immediately effective)
    - Continuous learning and improvement (RL training)
    - Automatic optimization (switch when ready)
    - Safety net (fallback if RL fails)
    """

    def __init__(
        self,
        server_url: str = "http://127.0.0.1:8000",
        enable_logging: bool = True,
        training_mode: bool = True,
        model_path: str = "models/hybrid_rl.pkl",
        switch_threshold: float = 0.85,
        min_samples_before_switch: int = 50,
        enable_fallback: bool = True
    ):
        """
        Initialize hybrid algorithm.

        Args:
            server_url: Elevator simulator server URL
            enable_logging: Whether to enable logging
            training_mode: Whether RL should train (False = use saved model only)
            model_path: Path to save/load RL model
            switch_threshold: Performance ratio threshold for switching to RL
            min_samples_before_switch: Minimum samples before considering switch
            enable_fallback: Whether to fallback to SCAN if RL degrades
        """
        super().__init__(server_url, enable_logging)

        # Store enable_logging before using it
        self.enable_logging_flag = enable_logging

        # Configuration
        self.training_mode = training_mode
        self.model_path = model_path
        self.enable_fallback = enable_fallback

        # Create sub-algorithms
        self.scan_algorithm = OptimizedScanAlgorithm(server_url, enable_logging=False)
        self.rl_algorithm = RLDQNAlgorithm(
            server_url,
            enable_logging=False,
            training_mode=training_mode,
            model_path=model_path
        )

        # Performance monitoring
        self.monitor = PerformanceMonitor(
            window_size=100,
            threshold_ratio=switch_threshold
        )
        self.min_samples_before_switch = min_samples_before_switch

        # State tracking
        self.active_algorithm = 'scan'  # Start with SCAN
        self.has_switched_to_rl = False
        self.switch_tick = None
        self.cold_start_duration = 0
        self.start_tick = 0

        # Statistics
        self.passengers_handled = 0
        self.scan_passengers = 0
        self.rl_passengers = 0

        if self.enable_logging_flag:
            self.log(f"Hybrid algorithm initialized")
            self.log(f"  Starting with: SCAN (cold start)")
            self.log(f"  Training mode: {training_mode}")
            self.log(f"  Switch threshold: {switch_threshold}")
            self.log(f"  Will switch to RL when: RL_wait <= {switch_threshold} * SCAN_wait")

    def on_init(self, elevators, floors):
        """Initialize both sub-algorithms"""
        super().on_init(elevators, floors)
        self.scan_algorithm.on_init(elevators, floors)
        self.rl_algorithm.on_init(elevators, floors)
        self.start_tick = 0

    def _check_and_switch_algorithm(self, tick: int):
        """
        Check if conditions are met to switch algorithm.

        Checks:
        1. If using SCAN and RL is ready -> switch to RL
        2. If using RL and performance degrades -> fallback to SCAN
        """
        # Only check periodically (every 10 passengers)
        if self.passengers_handled % 10 != 0:
            return

        # Check if we should switch from SCAN to RL
        if self.active_algorithm == 'scan' and not self.has_switched_to_rl:
            if self.monitor.should_use_rl(self.min_samples_before_switch):
                self._switch_to_rl(tick)

        # Check if we should fallback from RL to SCAN
        elif self.active_algorithm == 'rl' and self.enable_fallback:
            ratio = self.monitor.get_performance_ratio()
            if ratio is not None and ratio > 1.2:  # RL is 20% worse
                self._fallback_to_scan(tick)

    def _switch_to_rl(self, tick: int):
        """Switch from SCAN to RL"""
        self.active_algorithm = 'rl'
        self.has_switched_to_rl = True
        self.switch_tick = tick
        self.cold_start_duration = tick - self.start_tick

        if self.enable_logging_flag:
            ratio = self.monitor.get_performance_ratio()
            self.log(f"\n{'='*60}")
            self.log(f"SWITCHING TO RL ALGORITHM")
            self.log(f"{'='*60}")
            self.log(f"  Tick: {tick}")
            self.log(f"  Cold start duration: {self.cold_start_duration} ticks")
            self.log(f"  SCAN avg wait: {self.monitor.scan_avg_wait:.1f}")
            self.log(f"  RL avg wait: {self.monitor.rl_avg_wait:.1f}")
            self.log(f"  Performance ratio: {ratio:.2f}" if ratio else "  Performance ratio: N/A")
            self.log(f"  Passengers handled by SCAN: {self.scan_passengers}")
            self.log(f"  RL is now primary algorithm")
            self.log(f"{'='*60}\n")

    def _fallback_to_scan(self, tick: int):
        """Fallback from RL to SCAN"""
        self.active_algorithm = 'scan'

        if self.enable_logging_flag:
            ratio = self.monitor.get_performance_ratio()
            self.log(f"\n{'='*60}")
            self.log(f"FALLBACK TO SCAN ALGORITHM")
            self.log(f"{'='*60}")
            self.log(f"  Tick: {tick}")
            self.log(f"  Reason: RL performance degraded")
            self.log(f"  SCAN avg wait: {self.monitor.scan_avg_wait:.1f}")
            self.log(f"  RL avg wait: {self.monitor.rl_avg_wait:.1f}")
            self.log(f"  Performance ratio: {ratio:.2f}" if ratio else "  Performance ratio: N/A")
            self.log(f"{'='*60}\n")

    def on_passenger_call(self, passenger: ProxyPassenger, floor: ProxyFloor, direction: str) -> None:
        """Handle passenger call - record and delegate"""
        tick = self.get_current_tick()
        self.monitor.record_passenger_call(passenger.id, tick)

        # Delegate to active algorithm
        if self.active_algorithm == 'scan':
            self.scan_algorithm.on_passenger_call(passenger, floor, direction)
        else:
            self.rl_algorithm.on_passenger_call(passenger, floor, direction)

        # In training mode, also let RL observe (for learning)
        if self.training_mode and self.active_algorithm == 'scan':
            # RL observes but doesn't control
            pass

    def on_elevator_idle(self, elevator: ProxyElevator) -> None:
        """Handle idle elevator"""
        if self.active_algorithm == 'scan':
            self.scan_algorithm.on_elevator_idle(elevator)
        else:
            self.rl_algorithm.on_elevator_idle(elevator)

    def on_elevator_approaching(self, elevator: ProxyElevator, floor: ProxyFloor, direction: str) -> None:
        """Handle elevator approaching floor"""
        if self.active_algorithm == 'scan':
            self.scan_algorithm.on_elevator_approaching(elevator, floor, direction)
        else:
            self.rl_algorithm.on_elevator_approaching(elevator, floor, direction)

    def on_elevator_stopped(self, elevator: ProxyElevator, floor: ProxyFloor) -> None:
        """Handle elevator stopped"""
        if self.active_algorithm == 'scan':
            self.scan_algorithm.on_elevator_stopped(elevator, floor)
        else:
            self.rl_algorithm.on_elevator_stopped(elevator, floor)

    def on_passenger_board(self, elevator: ProxyElevator, passenger: ProxyPassenger) -> None:
        """Handle passenger boarding - record performance"""
        tick = self.get_current_tick()

        # Record to performance monitor
        self.monitor.record_passenger_board(passenger.id, tick, self.active_algorithm)

        # Update statistics
        self.passengers_handled += 1
        if self.active_algorithm == 'scan':
            self.scan_passengers += 1
        else:
            self.rl_passengers += 1

        # Delegate to active algorithm
        if self.active_algorithm == 'scan':
            self.scan_algorithm.on_passenger_board(elevator, passenger)
        else:
            self.rl_algorithm.on_passenger_board(elevator, passenger)

        # Check if we should switch algorithms
        self._check_and_switch_algorithm(tick)

    def on_tick(self, tick: int) -> None:
        """Handle simulation tick"""
        super().on_tick(tick)

        # Update active algorithm
        if self.active_algorithm == 'scan':
            self.scan_algorithm.on_tick(tick)
        else:
            self.rl_algorithm.on_tick(tick)

        # In training mode, also update RL for learning
        if self.training_mode and self.active_algorithm == 'scan':
            self.rl_algorithm.on_tick(tick)

    def get_current_tick(self) -> int:
        """Get current simulation tick"""
        # Use active algorithm's tick
        if self.active_algorithm == 'scan':
            return self.scan_algorithm.current_tick
        else:
            return self.rl_algorithm.current_tick

    def save_model(self, filepath: Optional[str] = None):
        """Save RL model"""
        if filepath is None:
            filepath = self.model_path

        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # Save RL model
        self.rl_algorithm.save_model(filepath)

        if self.enable_logging_flag:
            self.log(f"Hybrid algorithm RL model saved to {filepath}")

    def get_statistics(self) -> dict:
        """Get hybrid algorithm statistics"""
        stats = {
            'active_algorithm': self.active_algorithm,
            'has_switched_to_rl': self.has_switched_to_rl,
            'switch_tick': self.switch_tick,
            'cold_start_duration': self.cold_start_duration,
            'passengers_handled': self.passengers_handled,
            'scan_passengers': self.scan_passengers,
            'rl_passengers': self.rl_passengers,
            'scan_avg_wait': self.monitor.scan_avg_wait,
            'rl_avg_wait': self.monitor.rl_avg_wait,
            'performance_ratio': self.monitor.get_performance_ratio(),
        }
        return stats

    def print_statistics(self):
        """Print hybrid algorithm statistics"""
        stats = self.get_statistics()

        print("\n" + "="*60)
        print("HYBRID ALGORITHM STATISTICS")
        print("="*60)
        print(f"Active Algorithm: {stats['active_algorithm'].upper()}")
        print(f"Has Switched to RL: {stats['has_switched_to_rl']}")

        if stats['has_switched_to_rl']:
            print(f"Switch Tick: {stats['switch_tick']}")
            print(f"Cold Start Duration: {stats['cold_start_duration']} ticks")

        print(f"\nPassengers Handled:")
        print(f"  Total: {stats['passengers_handled']}")
        print(f"  By SCAN: {stats['scan_passengers']} ({100*stats['scan_passengers']/max(stats['passengers_handled'], 1):.1f}%)")
        print(f"  By RL: {stats['rl_passengers']} ({100*stats['rl_passengers']/max(stats['passengers_handled'], 1):.1f}%)")

        print(f"\nPerformance:")
        if stats['scan_avg_wait'] != float('inf'):
            print(f"  SCAN Average Wait: {stats['scan_avg_wait']:.1f} ticks")
        if stats['rl_avg_wait'] != float('inf'):
            print(f"  RL Average Wait: {stats['rl_avg_wait']:.1f} ticks")
        if stats['performance_ratio']:
            print(f"  Performance Ratio (RL/SCAN): {stats['performance_ratio']:.2f}")

        print("="*60 + "\n")
