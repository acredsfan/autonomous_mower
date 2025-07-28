#!/usr/bin/env python3
"""
Demo script for the predictive maintenance engine.

This script demonstrates the predictive maintenance engine by simulating
component wear and anomalies, and showing the resulting maintenance
recommendations and alerts.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mower.diagnostics.predictive_maintenance import (
    PredictiveMaintenanceEngine,
    ComponentWearData,
    ComponentWearLevel,
    MaintenanceType,
    MaintenancePriority
)
from src.mower.data_collection.telemetry_collector import TelemetryCollector
from src.mower.interfaces.telemetry import TelemetryDataPoint, TelemetryDataType, TelemetryPriority

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def simulate_telemetry_data(telemetry_collector, days_of_data=30, accelerated=True):
    """
    Simulate telemetry data for components over time.
    
    Args:
        telemetry_collector: Telemetry collector instance
        days_of_data: Number of days of data to simulate
        accelerated: If True, simulate data quickly
    """
    logger.info(f"Simulating {days_of_data} days of telemetry data...")
    
    # Start telemetry session
    session_id = telemetry_collector.start_session("predictive_maintenance_demo")
    
    # Components to simulate
    components = {
        'blade_motor': {
            'current_normal': 2.5,
            'temp_normal': 45.0,
            'usage_per_day': 6.0,  # hours
            'wear_rate': 0.5,  # % per day
            'anomaly_day': 20,  # day to introduce anomaly
        },
        'drive_motors': {
            'current_normal': 1.8,
            'temp_normal': 40.0,
            'usage_per_day': 8.0,  # hours
            'wear_rate': 0.3,  # % per day
            'anomaly_day': 25,  # day to introduce anomaly
        },
        'camera': {
            'current_normal': 0.5,
            'temp_normal': 35.0,
            'usage_per_day': 8.0,  # hours
            'wear_rate': 0.2,  # % per day
            'anomaly_day': None,  # no anomaly
        }
    }
    
    # Simulate data for each day
    for day in range(1, days_of_data + 1):
        logger.info(f"Simulating day {day}...")
        
        # Simulate data for each component
        for component_name, params in components.items():
            # Calculate wear based on day
            wear = day * params['wear_rate']
            
            # Check if anomaly should be introduced
            has_anomaly = params.get('anomaly_day') == day
            
            # Simulate multiple readings per day
            readings_per_day = 4 if accelerated else 24
            for hour in range(readings_per_day):
                # Calculate simulated values
                current = params['current_normal'] * (1.0 + wear / 100.0)
                temp = params['temp_normal'] * (1.0 + wear / 200.0)
                
                # Add anomaly if needed
                if has_anomaly:
                    current *= 1.5
                    temp *= 1.2
                    logger.info(f"Introducing anomaly for {component_name}")
                
                # Add some random variation
                import random
                current += random.uniform(-0.1, 0.1)
                temp += random.uniform(-1.0, 1.0)
                
                # Create telemetry data point
                telemetry_collector.collect_sensor_data(
                    sensor_name=component_name,
                    sensor_data={
                        'current': current,
                        'temperature': temp,
                        'usage_time': (params['usage_per_day'] / readings_per_day) * 3600  # seconds
                    }
                )
                
                # Add power consumption data
                telemetry_collector.collect_power_data({
                    'source': component_name,
                    'current': current,
                    'voltage': 12.0,
                    'cycles': 1
                })
            
            # Simulate maintenance event at day 15 for blade motor
            if component_name == 'blade_motor' and day == 15:
                telemetry_collector.collect_maintenance_event({
                    'component_name': component_name,
                    'maintenance_type': 'preventive',
                    'description': 'Routine blade motor maintenance',
                    'parts_used': ['lubricant'],
                    'timestamp': datetime.now().isoformat()
                })
        
        # Sleep between days
        if not accelerated:
            time.sleep(1.0)
    
    # End telemetry session
    telemetry_collector.end_session()
    logger.info("Telemetry simulation complete")


def run_demo(data_dir, days_to_simulate=30, accelerated=True):
    """
    Run the predictive maintenance demo.
    
    Args:
        data_dir: Directory to store data
        days_to_simulate: Number of days of data to simulate
        accelerated: If True, run the demo quickly
    """
    # Create data directory
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    
    # Create telemetry collector
    telemetry_collector = TelemetryCollector()
    
    # Create predictive maintenance engine
    config = {
        'data_dir': str(data_path),
        'analysis_interval': 1 if accelerated else 300,  # seconds
        'anomaly_threshold': -0.1,
        'wear_prediction_window': 30,
        'model_retrain_interval': 10 if accelerated else 86400  # seconds
    }
    
    engine = PredictiveMaintenanceEngine(
        telemetry_collector=telemetry_collector,
        config=config
    )
    
    # Start the engine
    engine.start()
    logger.info("Predictive maintenance engine started")
    
    try:
        # Simulate telemetry data
        simulate_telemetry_data(telemetry_collector, days_to_simulate, accelerated)
        
        # Wait for analysis to complete
        logger.info("Waiting for analysis to complete...")
        time.sleep(5 if accelerated else 30)
        
        # Display results
        logger.info("\n=== Predictive Maintenance Results ===")
        
        # Component wear data
        logger.info("\nComponent Wear Data:")
        for name, data in engine.get_component_wear_data().items():
            logger.info(f"  {name}: {data.wear_percentage:.1f}% worn, level: {data.wear_level.value}")
            if data.predicted_failure_date:
                days_to_failure = (data.predicted_failure_date - datetime.now()).days
                logger.info(f"    Predicted failure in {days_to_failure} days")
        
        # Maintenance recommendations
        logger.info("\nMaintenance Recommendations:")
        recommendations = engine.get_maintenance_recommendations()
        if recommendations:
            for rec in recommendations:
                logger.info(f"  {rec.component_name}: {rec.description}")
                logger.info(f"    Priority: {rec.priority.value}, Type: {rec.maintenance_type.value}")
                if rec.due_date:
                    logger.info(f"    Due date: {rec.due_date.strftime('%Y-%m-%d')}")
        else:
            logger.info("  No recommendations")
        
        # Maintenance alerts
        logger.info("\nMaintenance Alerts:")
        alerts = engine.get_maintenance_alerts()
        if alerts:
            for alert in alerts:
                logger.info(f"  {alert.component_name}: {alert.message}")
                logger.info(f"    Severity: {alert.severity.value}, Acknowledged: {alert.acknowledged}")
        else:
            logger.info("  No alerts")
        
        # System health summary
        logger.info("\nSystem Health Summary:")
        summary = engine.get_system_health_summary()
        logger.info(f"  Status: {summary['status']}")
        logger.info(f"  Components: {summary['total_components']}")
        logger.info(f"  Active alerts: {summary['active_alerts']}")
        logger.info(f"  Pending recommendations: {summary['pending_recommendations']}")
        
        # Maintenance schedule
        logger.info("\nMaintenance Schedule (next 30 days):")
        schedule = engine.get_maintenance_schedule(days_ahead=30)
        if schedule:
            for item in schedule:
                logger.info(f"  {item['date'][:10]}: {item['component']} - {item['description']}")
        else:
            logger.info("  No scheduled maintenance")
        
    finally:
        # Stop the engine
        engine.stop()
        telemetry_collector.stop()
        logger.info("Demo complete")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Predictive Maintenance Demo")
    parser.add_argument("--data-dir", default="data/predictive_maintenance_demo",
                      help="Directory to store data")
    parser.add_argument("--days", type=int, default=30,
                      help="Number of days to simulate")
    parser.add_argument("--real-time", action="store_true",
                      help="Run in real-time mode (slower)")
    
    args = parser.parse_args()
    
    run_demo(args.data_dir, args.days, not args.real_time)


if __name__ == "__main__":
    main()