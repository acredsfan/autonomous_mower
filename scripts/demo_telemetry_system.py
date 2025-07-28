#!/usr/bin/env python3
"""
Demonstration script for the telemetry data collection system.

This script shows how to use the comprehensive telemetry system
for data collection, storage, and analysis.
"""

import time
import random
from datetime import datetime

from mower.data_collection.telemetry_integration import TelemetrySystem


def main():
    """Demonstrate the telemetry system functionality."""
    print("🔧 Autonomous Mower Telemetry System Demo")
    print("=" * 50)
    
    # Configure telemetry system
    config = {
        'storage': {
            'backend': 'sqlite',
            'sqlite_path': 'data/demo_telemetry.db',
            'retention_days': 7
        },
        'collector': {
            'buffer_size': 50,
            'flush_interval': 5,
            'max_queue_size': 1000
        }
    }
    
    # Initialize telemetry system
    print("📊 Initializing telemetry system...")
    telemetry = TelemetrySystem(config)
    
    try:
        # Start a telemetry session
        print("🚀 Starting telemetry session...")
        session_id = telemetry.start_session("demo_session")
        print(f"   Session ID: {session_id}")
        
        # Simulate mower operation with telemetry collection
        print("\n🤖 Simulating mower operation...")
        
        for i in range(20):
            # Simulate sensor readings
            temperature = 20 + random.uniform(-5, 15)
            humidity = 50 + random.uniform(-20, 30)
            telemetry.collect_sensor_data("environmental", {
                "temperature": temperature,
                "humidity": humidity,
                "timestamp": datetime.now().isoformat()
            })
            
            # Simulate performance metrics
            cpu_usage = 30 + random.uniform(0, 40)
            memory_usage = 40 + random.uniform(0, 30)
            telemetry.collect_performance_metric("system_performance", {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "frame_processing_time": random.uniform(50, 150)
            })
            
            # Simulate navigation data
            lat = 40.7128 + random.uniform(-0.001, 0.001)
            lon = -74.0060 + random.uniform(-0.001, 0.001)
            telemetry.collect_navigation_data({
                "latitude": lat,
                "longitude": lon,
                "speed": random.uniform(0.5, 2.0),
                "heading": random.uniform(0, 360)
            })
            
            # Simulate power consumption
            voltage = 12.0 + random.uniform(-0.5, 0.8)
            current = 1.5 + random.uniform(0, 1.0)
            telemetry.collect_power_data({
                "voltage": voltage,
                "current": current,
                "power": voltage * current
            })
            
            # Occasionally simulate system events
            if i % 5 == 0:
                telemetry.collect_system_event("status_update", {
                    "status": "operating",
                    "progress": f"{(i/20)*100:.1f}%",
                    "area_covered": i * 10.5
                })
            
            # Simulate an error event
            if i == 15:
                telemetry.collect_error_event("sensor_warning", {
                    "sensor": "temperature",
                    "message": "Temperature reading slightly elevated",
                    "value": temperature
                })
            
            print(f"   📈 Collected data point {i+1}/20")
            time.sleep(0.2)  # Small delay to simulate real operation
        
        # Wait for data to be processed
        print("\n⏳ Processing collected data...")
        time.sleep(3)
        
        # Display statistics
        print("\n📊 Telemetry Statistics:")
        stats = telemetry.get_statistics()
        print(f"   System Status: {stats['system_status']}")
        print(f"   Total Collected: {stats['collector']['total_collected']}")
        print(f"   Total Stored: {stats['collector']['total_stored']}")
        print(f"   Storage Records: {stats['storage']['total_records']}")
        
        # Analyze performance trends
        print("\n📈 Performance Analysis:")
        cpu_analysis = telemetry.analyze_performance_trends("system_performance")
        if cpu_analysis['status'] == 'success':
            stats_data = cpu_analysis['statistics']
            print(f"   CPU Usage - Mean: {stats_data['mean']:.1f}%, Max: {stats_data['max']:.1f}%")
            if 'trend' in cpu_analysis:
                print(f"   Trend: {cpu_analysis['trend']['direction']}")
        
        # Generate summary report
        print("\n📋 Session Summary Report:")
        report = telemetry.generate_summary_report(session_id)
        if report['status'] == 'success':
            print(f"   Total Data Points: {report['total_data_points']}")
            print(f"   Data Types: {list(report['data_distribution']['by_type'].keys())}")
            if 'issues' in report and report['issues']:
                print(f"   Issues Detected: {len(report['issues'])}")
        
        # Calculate efficiency metrics
        print("\n⚡ Efficiency Metrics:")
        efficiency = telemetry.calculate_efficiency_metrics(session_id)
        if efficiency['status'] == 'success':
            if 'power_efficiency' in efficiency:
                power_eff = efficiency['power_efficiency']
                print(f"   Average Power: {power_eff.get('average_power', 0):.2f}W")
                print(f"   Average Voltage: {power_eff.get('average_voltage', 0):.2f}V")
            if 'processing_efficiency' in efficiency:
                proc_eff = efficiency['processing_efficiency']
                print(f"   Average CPU: {proc_eff.get('average_cpu_usage', 0):.1f}%")
                print(f"   Average Memory: {proc_eff.get('average_memory_usage', 0):.1f}%")
        
        # Detect anomalies
        print("\n🚨 Anomaly Detection:")
        anomalies = telemetry.detect_anomalies("performance_metric", "system_performance")
        if anomalies:
            print(f"   Found {len(anomalies)} anomalies")
            for anomaly in anomalies[:3]:  # Show first 3
                print(f"   - {anomaly['type']}: {anomaly.get('metric', 'unknown')} = {anomaly.get('value', 'N/A')}")
        else:
            print("   No anomalies detected")
        
        # Export data sample
        print("\n💾 Data Export Sample:")
        json_export = telemetry.export_data(format_type='json')
        if json_export:
            import json
            data = json.loads(json_export)
            print(f"   Exported {len(data)} records as JSON")
            if data:
                print(f"   Sample record: {data[0]['data_type']} from {data[0]['source']}")
        
        # End session
        print(f"\n🏁 Ending telemetry session...")
        ended_session = telemetry.end_session()
        print(f"   Ended session: {ended_session}")
        
        print("\n✅ Telemetry system demonstration completed successfully!")
        print("\n💡 Key Features Demonstrated:")
        print("   • Multi-type data collection (sensors, performance, navigation, power)")
        print("   • Real-time data processing and storage")
        print("   • Performance trend analysis")
        print("   • Anomaly detection")
        print("   • Efficiency metrics calculation")
        print("   • Data export capabilities")
        print("   • Session management")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        
    finally:
        # Shutdown telemetry system
        print("\n🔄 Shutting down telemetry system...")
        telemetry.shutdown()
        print("   Shutdown complete")


if __name__ == "__main__":
    main()