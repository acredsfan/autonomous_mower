#!/usr/bin/env python3
"""
Demo script for ML pattern optimization.

This script demonstrates the machine learning pattern optimization
functionality by simulating mowing sessions and showing how the
system learns to select better patterns over time.
"""

import argparse
import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from mower.navigation.path_planner import PathPlanner, PatternConfig, PatternType
from mower.navigation.ml_integration import IntelligentPathPlanner
from mower.navigation.ml_pattern_optimizer import (
    EnvironmentState,
    PatternPerformanceMetrics,
    ReinforcementLearningOptimizer
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockTelemetryCollector:
    """Mock telemetry collector for demo."""
    
    def __init__(self):
        self.events = []
        self.metrics = []
        self.sensor_data = []
        self.current_session = None
    
    def start_session(self, session_name=None):
        self.current_session = f"demo_session_{int(time.time())}"
        logger.info(f"Started telemetry session: {self.current_session}")
        return self.current_session
    
    def end_session(self):
        if self.current_session:
            logger.info(f"Ended telemetry session: {self.current_session}")
            self.current_session = None
        return self.current_session
    
    def collect_system_event(self, event_name, event_data, priority=None):
        self.events.append({
            'timestamp': datetime.now().isoformat(),
            'event': event_name,
            'data': event_data,
            'priority': priority
        })
        return True
    
    def collect_performance_metric(self, metric_name, metric_data, priority=None):
        self.metrics.append({
            'timestamp': datetime.now().isoformat(),
            'metric': metric_name,
            'data': metric_data,
            'priority': priority
        })
        return True
    
    def collect_sensor_data(self, sensor_name, sensor_data, priority=None):
        self.sensor_data.append({
            'timestamp': datetime.now().isoformat(),
            'sensor': sensor_name,
            'data': sensor_data,
            'priority': priority
        })
        return True


class MockResourceManager:
    """Mock resource manager for demo."""
    
    def __init__(self):
        self.battery_level = 100
        self.weather_conditions = {
            'temperature': 22,
            'humidity': 60,
            'wind_speed': 8,
            'precipitation': 0
        }
    
    def get_battery_status(self):
        # Simulate battery drain
        self.battery_level = max(20, self.battery_level - random.randint(5, 15))
        return {'level': self.battery_level}
    
    def get_weather_info(self):
        # Simulate changing weather
        self.weather_conditions['temperature'] += random.uniform(-2, 2)
        self.weather_conditions['humidity'] += random.uniform(-5, 5)
        self.weather_conditions['wind_speed'] += random.uniform(-2, 2)
        
        # Clamp values to reasonable ranges
        self.weather_conditions['temperature'] = max(10, min(35, self.weather_conditions['temperature']))
        self.weather_conditions['humidity'] = max(30, min(90, self.weather_conditions['humidity']))
        self.weather_conditions['wind_speed'] = max(0, min(25, self.weather_conditions['wind_speed']))
        
        return self.weather_conditions


def create_demo_environment(scenario='normal'):
    """Create demo environment based on scenario."""
    base_env = {
        'lawn_area': 1000.0,
        'obstacle_density': 0.1,
        'terrain_slope': 5.0,
        'grass_height': 5.0,
        'weather_score': 0.8,
        'time_of_day': 10,
        'season': 1,
        'battery_level': 0.9,
        'blade_sharpness': 0.8
    }
    
    if scenario == 'small_lawn':
        base_env.update({
            'lawn_area': 300.0,
            'obstacle_density': 0.05,
            'terrain_slope': 2.0
        })
    elif scenario == 'large_lawn':
        base_env.update({
            'lawn_area': 3000.0,
            'obstacle_density': 0.15,
            'terrain_slope': 8.0
        })
    elif scenario == 'obstacles':
        base_env.update({
            'obstacle_density': 0.3,
            'terrain_slope': 10.0
        })
    elif scenario == 'poor_weather':
        base_env.update({
            'weather_score': 0.4,
            'grass_height': 12.0
        })
    
    return base_env


def simulate_mowing_performance(pattern_type, environment, add_noise=True):
    """Simulate mowing performance based on pattern and environment."""
    # Base performance values
    base_time = 3600.0  # 1 hour
    base_distance = 1000.0  # 1 km
    base_energy = 250.0  # 250 Wh
    base_efficiency = 0.8
    base_obstacles = 3
    
    # Pattern-specific modifiers
    pattern_modifiers = {
        PatternType.PARALLEL: {
            'time_factor': 1.0,
            'energy_factor': 1.0,
            'efficiency_factor': 1.0,
            'obstacle_factor': 1.0
        },
        PatternType.SPIRAL: {
            'time_factor': 1.1,
            'energy_factor': 0.9,
            'efficiency_factor': 1.1,
            'obstacle_factor': 0.8
        },
        PatternType.ZIGZAG: {
            'time_factor': 0.9,
            'energy_factor': 1.1,
            'efficiency_factor': 0.9,
            'obstacle_factor': 1.2
        },
        PatternType.CHECKERBOARD: {
            'time_factor': 1.2,
            'energy_factor': 1.0,
            'efficiency_factor': 1.2,
            'obstacle_factor': 0.9
        },
        PatternType.DIAMOND: {
            'time_factor': 1.1,
            'energy_factor': 1.05,
            'efficiency_factor': 1.05,
            'obstacle_factor': 1.0
        }
    }
    
    modifiers = pattern_modifiers.get(pattern_type, pattern_modifiers[PatternType.PARALLEL])
    
    # Environment-specific adjustments
    area_factor = environment['lawn_area'] / 1000.0
    obstacle_factor = 1.0 + environment['obstacle_density']
    slope_factor = 1.0 + (environment['terrain_slope'] / 45.0) * 0.3
    weather_factor = environment['weather_score']
    grass_factor = 1.0 + (environment['grass_height'] / 20.0) * 0.2
    
    # Calculate performance metrics
    total_time = base_time * area_factor * modifiers['time_factor'] * obstacle_factor * slope_factor / weather_factor
    total_distance = base_distance * area_factor
    energy_consumption = base_energy * area_factor * modifiers['energy_factor'] * slope_factor * grass_factor
    coverage_efficiency = base_efficiency * modifiers['efficiency_factor'] * weather_factor / obstacle_factor
    obstacle_encounters = int(base_obstacles * modifiers['obstacle_factor'] * environment['obstacle_density'] * 10)
    
    # Add some randomness if requested
    if add_noise:
        total_time *= random.uniform(0.9, 1.1)
        energy_consumption *= random.uniform(0.9, 1.1)
        coverage_efficiency *= random.uniform(0.95, 1.05)
        obstacle_encounters += random.randint(-1, 2)
    
    # Clamp values to reasonable ranges
    coverage_efficiency = max(0.3, min(1.0, coverage_efficiency))
    obstacle_encounters = max(0, obstacle_encounters)
    completion_rate = max(0.7, min(1.0, coverage_efficiency * weather_factor))
    
    return PatternPerformanceMetrics(
        pattern_type=pattern_type,
        total_time=total_time,
        total_distance=total_distance,
        energy_consumption=energy_consumption,
        coverage_efficiency=coverage_efficiency,
        obstacle_encounters=obstacle_encounters,
        weather_conditions=environment,
        terrain_difficulty=environment['terrain_slope'] / 45.0,
        blade_wear=1.0 - environment['blade_sharpness'],
        completion_rate=completion_rate
    )


def run_learning_demo(num_episodes=20, scenarios=None):
    """Run learning demonstration."""
    logger.info("Starting ML Pattern Optimization Demo")
    
    # Create demo components
    pattern_config = PatternConfig(
        pattern_type=PatternType.PARALLEL,
        spacing=0.5,
        angle=0.0,
        overlap=0.1,
        start_point=(0.0, 0.0),
        boundary_points=[(0, 0), (20, 0), (20, 20), (0, 20)]
    )
    
    base_planner = PathPlanner(pattern_config)
    mock_telemetry = MockTelemetryCollector()
    mock_resource_manager = MockResourceManager()
    
    # Create intelligent planner
    intelligent_planner = IntelligentPathPlanner(
        base_path_planner=base_planner,
        telemetry_collector=mock_telemetry,
        resource_manager=mock_resource_manager,
        enable_ml=True,
        ml_confidence_threshold=0.5
    )
    
    # Default scenarios if none provided
    if scenarios is None:
        scenarios = ['normal', 'small_lawn', 'large_lawn', 'obstacles', 'poor_weather']
    
    logger.info(f"Running {num_episodes} episodes with scenarios: {scenarios}")
    
    # Track performance over time
    episode_results = []
    
    for episode in range(num_episodes):
        # Select random scenario
        scenario = random.choice(scenarios)
        environment_data = create_demo_environment(scenario)
        
        logger.info(f"\nEpisode {episode + 1}/{num_episodes} - Scenario: {scenario}")
        
        # Generate path (this will select pattern using ML)
        path = intelligent_planner.generate_optimized_path(environment_data=environment_data)
        selected_pattern = intelligent_planner.session_pattern
        
        logger.info(f"Selected pattern: {selected_pattern.name}")
        
        # Simulate mowing performance
        performance = simulate_mowing_performance(selected_pattern, environment_data)
        
        # Complete the session
        intelligent_planner.complete_mowing_session(
            total_time=performance.total_time,
            total_distance=performance.total_distance,
            energy_consumption=performance.energy_consumption,
            coverage_efficiency=performance.coverage_efficiency,
            obstacle_encounters=performance.obstacle_encounters,
            completion_rate=performance.completion_rate
        )
        
        # Record results
        episode_results.append({
            'episode': episode + 1,
            'scenario': scenario,
            'pattern': selected_pattern.name,
            'efficiency': performance.coverage_efficiency,
            'energy': performance.energy_consumption,
            'time': performance.total_time,
            'obstacles': performance.obstacle_encounters,
            'completion': performance.completion_rate
        })
        
        logger.info(f"Performance - Efficiency: {performance.coverage_efficiency:.3f}, "
                   f"Energy: {performance.energy_consumption:.1f}Wh, "
                   f"Time: {performance.total_time/60:.1f}min")
        
        # Show learning progress every 5 episodes
        if (episode + 1) % 5 == 0:
            stats = intelligent_planner.get_ml_statistics()
            optimizer_stats = stats.get('optimizer', {})
            logger.info(f"Learning progress - Episodes: {optimizer_stats.get('training_episodes', 0)}, "
                       f"Exploration rate: {optimizer_stats.get('exploration_rate', 0):.3f}")
    
    return intelligent_planner, episode_results


def analyze_results(episode_results):
    """Analyze and display results."""
    logger.info("\n" + "="*60)
    logger.info("LEARNING ANALYSIS")
    logger.info("="*60)
    
    # Group results by scenario
    scenario_results = {}
    for result in episode_results:
        scenario = result['scenario']
        if scenario not in scenario_results:
            scenario_results[scenario] = []
        scenario_results[scenario].append(result)
    
    # Analyze each scenario
    for scenario, results in scenario_results.items():
        logger.info(f"\nScenario: {scenario.upper()}")
        logger.info("-" * 40)
        
        # Pattern usage
        pattern_counts = {}
        total_efficiency = 0
        total_energy = 0
        
        for result in results:
            pattern = result['pattern']
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            total_efficiency += result['efficiency']
            total_energy += result['energy']
        
        logger.info("Pattern usage:")
        for pattern, count in sorted(pattern_counts.items()):
            percentage = (count / len(results)) * 100
            logger.info(f"  {pattern}: {count} times ({percentage:.1f}%)")
        
        avg_efficiency = total_efficiency / len(results)
        avg_energy = total_energy / len(results)
        
        logger.info(f"Average efficiency: {avg_efficiency:.3f}")
        logger.info(f"Average energy: {avg_energy:.1f}Wh")
    
    # Show learning trend
    logger.info(f"\nLEARNING TREND")
    logger.info("-" * 40)
    
    # Compare first half vs second half
    mid_point = len(episode_results) // 2
    first_half = episode_results[:mid_point]
    second_half = episode_results[mid_point:]
    
    first_avg_efficiency = sum(r['efficiency'] for r in first_half) / len(first_half)
    second_avg_efficiency = sum(r['efficiency'] for r in second_half) / len(second_half)
    
    first_avg_energy = sum(r['energy'] for r in first_half) / len(first_half)
    second_avg_energy = sum(r['energy'] for r in second_half) / len(second_half)
    
    logger.info(f"First half average efficiency: {first_avg_efficiency:.3f}")
    logger.info(f"Second half average efficiency: {second_avg_efficiency:.3f}")
    logger.info(f"Efficiency improvement: {((second_avg_efficiency - first_avg_efficiency) / first_avg_efficiency * 100):+.1f}%")
    
    logger.info(f"First half average energy: {first_avg_energy:.1f}Wh")
    logger.info(f"Second half average energy: {second_avg_energy:.1f}Wh")
    logger.info(f"Energy improvement: {((first_avg_energy - second_avg_energy) / first_avg_energy * 100):+.1f}%")


def demonstrate_recommendations(intelligent_planner):
    """Demonstrate pattern recommendations for different scenarios."""
    logger.info("\n" + "="*60)
    logger.info("PATTERN RECOMMENDATIONS")
    logger.info("="*60)
    
    scenarios = {
        'Small Lawn': create_demo_environment('small_lawn'),
        'Large Lawn': create_demo_environment('large_lawn'),
        'Obstacle-Rich': create_demo_environment('obstacles'),
        'Poor Weather': create_demo_environment('poor_weather')
    }
    
    for scenario_name, environment_data in scenarios.items():
        logger.info(f"\n{scenario_name}:")
        logger.info("-" * 30)
        
        recommendations = intelligent_planner.get_pattern_recommendations(environment_data)
        
        if recommendations:
            for i, rec in enumerate(recommendations[:3], 1):
                status = "✓ RECOMMENDED" if rec['recommended'] else "  Not recommended"
                logger.info(f"{i}. {rec['pattern_type']:<12} "
                           f"(confidence: {rec['confidence']:.3f}) {status}")
        else:
            logger.info("No recommendations available yet")


def save_results(episode_results, intelligent_planner, output_file=None):
    """Save results to file."""
    if output_file is None:
        output_file = f"ml_demo_results_{int(time.time())}.json"
    
    results_data = {
        'timestamp': datetime.now().isoformat(),
        'episodes': episode_results,
        'ml_statistics': intelligent_planner.get_ml_statistics(),
        'pattern_analysis': {}
    }
    
    # Add pattern analysis for each pattern type
    for pattern_type in PatternType:
        try:
            analysis = intelligent_planner.get_pattern_analysis(pattern_type)
            results_data['pattern_analysis'][pattern_type.name] = analysis
        except Exception as e:
            logger.warning(f"Could not analyze pattern {pattern_type.name}: {e}")
    
    with open(output_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    logger.info(f"\nResults saved to: {output_file}")


def main():
    """Main demo function."""
    parser = argparse.ArgumentParser(description='ML Pattern Optimization Demo')
    parser.add_argument('--episodes', type=int, default=20,
                       help='Number of episodes to run (default: 20)')
    parser.add_argument('--scenarios', nargs='+',
                       choices=['normal', 'small_lawn', 'large_lawn', 'obstacles', 'poor_weather'],
                       help='Scenarios to include in demo')
    parser.add_argument('--output', type=str,
                       help='Output file for results (default: auto-generated)')
    parser.add_argument('--quiet', action='store_true',
                       help='Reduce logging output')
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    try:
        # Run the learning demo
        intelligent_planner, episode_results = run_learning_demo(
            num_episodes=args.episodes,
            scenarios=args.scenarios
        )
        
        # Analyze results
        analyze_results(episode_results)
        
        # Show recommendations
        demonstrate_recommendations(intelligent_planner)
        
        # Save results
        save_results(episode_results, intelligent_planner, args.output)
        
        logger.info("\n" + "="*60)
        logger.info("DEMO COMPLETED SUCCESSFULLY")
        logger.info("="*60)
        
    except KeyboardInterrupt:
        logger.info("\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        raise


if __name__ == '__main__':
    main()