"""
Heartbeat Monitoring System

This module monitors service heartbeats and triggers alerts when services
miss consecutive expected heartbeats.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys


class HeartbeatMonitor:
    """
    Monitors service heartbeats and detects missed heartbeat patterns.
    
    Attributes:
        expected_interval_seconds (int): Expected time between heartbeats
        allowed_misses (int): Number of consecutive misses before alerting
    """
    
    def __init__(self, expected_interval_seconds: int, allowed_misses: int):
        """
        Initialize the heartbeat monitor.
        
        Args:
            expected_interval_seconds: Expected interval between heartbeats in seconds
            allowed_misses: Number of consecutive missed heartbeats before alert
        """
        if expected_interval_seconds <= 0:
            raise ValueError("expected_interval_seconds must be positive")
        if allowed_misses <= 0:
            raise ValueError("allowed_misses must be positive")
            
        self.expected_interval_seconds = expected_interval_seconds
        self.allowed_misses = allowed_misses
    
    def parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """
        Parse ISO 8601 timestamp string to datetime object.
        
        Args:
            timestamp_str: ISO 8601 formatted timestamp string
            
        Returns:
            datetime object or None if parsing fails
        """
        try:
            # Handle both with and without 'Z' suffix
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, AttributeError, TypeError):
            return None
    
    def validate_event(self, event: Dict) -> bool:
        """
        Validate that an event has required fields and valid data.
        
        Args:
            event: Dictionary containing heartbeat event data
            
        Returns:
            True if event is valid, False otherwise
        """
        if not isinstance(event, dict):
            return False
        
        # Check required fields
        if 'service' not in event or 'timestamp' not in event:
            return False
        
        # Validate service name
        if not isinstance(event['service'], str) or not event['service'].strip():
            return False
        
        # Validate timestamp
        if self.parse_timestamp(event['timestamp']) is None:
            return False
        
        return True
    
    def load_events(self, filepath: str) -> List[Dict]:
        """
        Load and validate events from JSON file.
        
        Args:
            filepath: Path to JSON file containing heartbeat events
            
        Returns:
            List of valid heartbeat events
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Handle both single object and array formats
            if isinstance(data, dict):
                events = [data]
            elif isinstance(data, list):
                events = data
            else:
                print(f"Warning: Unexpected JSON format in {filepath}", file=sys.stderr)
                return []
            
            # Filter valid events
            valid_events = []
            for i, event in enumerate(events):
                if self.validate_event(event):
                    valid_events.append(event)
                else:
                    print(f"Warning: Skipping malformed event at index {i}: {event}", 
                          file=sys.stderr)
            
            return valid_events
            
        except FileNotFoundError:
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            return []
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {filepath}: {e}", file=sys.stderr)
            return []
    
    def group_and_sort_events(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group events by service and sort chronologically.
        
        Args:
            events: List of heartbeat events
            
        Returns:
            Dictionary mapping service names to sorted event lists
        """
        service_events = {}
        
        for event in events:
            service = event['service']
            if service not in service_events:
                service_events[service] = []
            service_events[service].append(event)
        
        # Sort each service's events by timestamp
        for service in service_events:
            service_events[service].sort(
                key=lambda e: self.parse_timestamp(e['timestamp'])
            )
        
        return service_events
    
    def detect_missed_heartbeats(self, events: List[Dict]) -> Optional[Dict]:
        """
        Detect if a service has missed consecutive heartbeats.
        
        Args:
            events: Sorted list of heartbeat events for a single service
            
        Returns:
            Alert dictionary if threshold exceeded, None otherwise
        """
        if not events:
            return None
        
        service_name = events[0]['service']
        consecutive_misses = 0
        
        for i in range(len(events) - 1):
            current_time = self.parse_timestamp(events[i]['timestamp'])
            next_time = self.parse_timestamp(events[i + 1]['timestamp'])
            
            expected_next = current_time + timedelta(seconds=self.expected_interval_seconds)
            time_diff = (next_time - expected_next).total_seconds()
            
            # Check if next heartbeat is late (allowing small tolerance for timing)
            if time_diff >= self.expected_interval_seconds * 0.9:
                # Calculate how many intervals were missed
                intervals_missed = round(time_diff / self.expected_interval_seconds)
                consecutive_misses += intervals_missed
                
                # Check if threshold exceeded
                if consecutive_misses >= self.allowed_misses:
                    # Alert time is when the threshold was crossed
                    alert_time = expected_next + timedelta(
                        seconds=self.expected_interval_seconds * (self.allowed_misses - 1)
                    )
                    return {
                        'service': service_name,
                        'alert_at': alert_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                    }
            else:
                # Reset counter if heartbeat received on time
                consecutive_misses = 0
        
        return None
    
    def monitor(self, events: List[Dict]) -> List[Dict]:
        """
        Monitor all services and generate alerts for missed heartbeats.
        
        Args:
            events: List of heartbeat events from all services
            
        Returns:
            List of alert dictionaries for services that exceeded miss threshold
        """
        # Group and sort events by service
        service_events = self.group_and_sort_events(events)
        
        # Check each service for missed heartbeats
        alerts = []
        for service, service_event_list in service_events.items():
            alert = self.detect_missed_heartbeats(service_event_list)
            if alert:
                alerts.append(alert)
        
        return alerts


def main():
    """
    Main entry point for the heartbeat monitoring system.
    """
    # Configuration
    EXPECTED_INTERVAL_SECONDS = 60
    ALLOWED_MISSES = 3
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python main.py <heartbeat_file.json>")
        print("\nExample: python main.py sample_data/heartbeats.json")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    # Initialize monitor
    monitor = HeartbeatMonitor(EXPECTED_INTERVAL_SECONDS, ALLOWED_MISSES)
    
    # Load events
    print(f"Loading heartbeat events from {filepath}...")
    events = monitor.load_events(filepath)
    print(f"Loaded {len(events)} valid events\n")
    
    # Monitor and generate alerts
    alerts = monitor.monitor(events)
    
    # Display results
    if alerts:
        print(f"⚠️  ALERTS TRIGGERED: {len(alerts)}")
        print(json.dumps(alerts, indent=2))
    else:
        print("✓ No alerts - all services are healthy")
    
    return alerts


if __name__ == "__main__":
    main()
    