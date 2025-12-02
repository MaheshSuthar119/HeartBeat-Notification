"""
Test suite for Heartbeat Monitoring System

Tests cover:
- Working alert cases
- Near-miss scenarios (no alert)
- Unordered input handling
- Malformed event handling
- Edge cases
"""

import unittest
from datetime import datetime, timedelta
from main import HeartbeatMonitor
import json
import tempfile
import os


class TestHeartbeatMonitor(unittest.TestCase):
    """Test cases for HeartbeatMonitor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = HeartbeatMonitor(
            expected_interval_seconds=60,
            allowed_misses=3
        )
    
    def test_working_alert_case(self):
        """Test Case 1: Service misses 3+ heartbeats and triggers alert"""
        events = [
            {"service": "email", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "email", "timestamp": "2025-08-04T10:01:00Z"},
            {"service": "email", "timestamp": "2025-08-04T10:02:00Z"},
            # Missing 3 heartbeats (10:03, 10:04, 10:05)
            {"service": "email", "timestamp": "2025-08-04T10:06:00Z"},
        ]
        
        alerts = self.monitor.monitor(events)
        
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['service'], 'email')
        self.assertEqual(alerts[0]['alert_at'], '2025-08-04T10:05:00Z')
        print("✓ Test 1 passed: Working alert case")
    
    def test_near_miss_no_alert(self):
        """Test Case 2: Service misses only 2 heartbeats - no alert"""
        events = [
            {"service": "database", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "database", "timestamp": "2025-08-04T10:01:00Z"},
            # Missing 2 heartbeats (10:02, 10:03)
            {"service": "database", "timestamp": "2025-08-04T10:04:00Z"},
            {"service": "database", "timestamp": "2025-08-04T10:05:00Z"},
        ]
        
        alerts = self.monitor.monitor(events)
        
        self.assertEqual(len(alerts), 0)
        print("✓ Test 2 passed: Near-miss case (no alert)")
    
    def test_unordered_input(self):
        """Test Case 3: Heartbeats arrive out of chronological order"""
        events = [
            {"service": "api", "timestamp": "2025-08-04T10:06:00Z"},
            {"service": "api", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "api", "timestamp": "2025-08-04T10:02:00Z"},
            {"service": "api", "timestamp": "2025-08-04T10:01:00Z"},
        ]
        
        # Should sort and detect 3 missed heartbeats between 10:02 and 10:06
        alerts = self.monitor.monitor(events)
        
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['service'], 'api')
        print("✓ Test 3 passed: Unordered input handling")
    
    def test_malformed_events(self):
        """Test Case 4: Handle malformed events gracefully"""
        events = [
            {"service": "cache", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "cache"},  # Missing timestamp
            {"timestamp": "2025-08-04T10:01:00Z"},  # Missing service
            {"service": "cache", "timestamp": "invalid-timestamp"},  # Bad timestamp
            {"service": "", "timestamp": "2025-08-04T10:02:00Z"},  # Empty service
            None,  # Null event
            "not a dict",  # Wrong type
            {"service": "cache", "timestamp": "2025-08-04T10:03:00Z"},
        ]
        
        # Should skip malformed events and process valid ones
        valid_events = [e for e in events if self.monitor.validate_event(e)]
        
        self.assertEqual(len(valid_events), 2)
        alerts = self.monitor.monitor(events)
        self.assertEqual(len(alerts), 0)  # Not enough valid events to trigger
        print("✓ Test 4 passed: Malformed event handling")
    
    def test_multiple_services(self):
        """Test Case 5: Monitor multiple services simultaneously"""
        events = [
            {"service": "email", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "sms", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "email", "timestamp": "2025-08-04T10:01:00Z"},
            {"service": "sms", "timestamp": "2025-08-04T10:01:00Z"},
            # Email misses 3 heartbeats
            {"service": "email", "timestamp": "2025-08-04T10:05:00Z"},
            # SMS continues normally
            {"service": "sms", "timestamp": "2025-08-04T10:02:00Z"},
            {"service": "sms", "timestamp": "2025-08-04T10:03:00Z"},
        ]
        
        alerts = self.monitor.monitor(events)
        
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['service'], 'email')
        print("✓ Test 5 passed: Multiple services")
    
    def test_exact_threshold(self):
        """Test Case 6: Exactly 3 misses triggers alert"""
        events = [
            {"service": "worker", "timestamp": "2025-08-04T10:00:00Z"},
            # Miss exactly 3 (10:01, 10:02, 10:03)
            {"service": "worker", "timestamp": "2025-08-04T10:04:00Z"},
        ]
        
        alerts = self.monitor.monitor(events)
        
        self.assertEqual(len(alerts), 1)
        print("✓ Test 6 passed: Exact threshold")
    
    def test_recovery_after_misses(self):
        """Test Case 7: Service recovers after missing heartbeats"""
        events = [
            {"service": "monitor", "timestamp": "2025-08-04T10:00:00Z"},
            # Miss 2 heartbeats
            {"service": "monitor", "timestamp": "2025-08-04T10:03:00Z"},
            # Recover with regular heartbeats
            {"service": "monitor", "timestamp": "2025-08-04T10:04:00Z"},
            {"service": "monitor", "timestamp": "2025-08-04T10:05:00Z"},
            # Miss 2 more (not consecutive from first set)
            {"service": "monitor", "timestamp": "2025-08-04T10:08:00Z"},
        ]
        
        alerts = self.monitor.monitor(events)
        
        self.assertEqual(len(alerts), 0)
        print("✓ Test 7 passed: Recovery after misses")
    
    def test_empty_events(self):
        """Test Case 8: Handle empty event list"""
        events = []
        alerts = self.monitor.monitor(events)
        
        self.assertEqual(len(alerts), 0)
        print("✓ Test 8 passed: Empty events")
    
    def test_single_event(self):
        """Test Case 9: Single event doesn't trigger alert"""
        events = [
            {"service": "solo", "timestamp": "2025-08-04T10:00:00Z"}
        ]
        
        alerts = self.monitor.monitor(events)
        
        self.assertEqual(len(alerts), 0)
        print("✓ Test 9 passed: Single event")
    
    def test_load_from_file(self):
        """Test Case 10: Load events from JSON file"""
        test_data = [
            {"service": "file-test", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "file-test", "timestamp": "2025-08-04T10:01:00Z"},
            {"service": "file-test", "timestamp": "2025-08-04T10:05:00Z"},
        ]
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(test_data, f)
            temp_path = f.name
        
        try:
            events = self.monitor.load_events(temp_path)
            self.assertEqual(len(events), 3)
            
            alerts = self.monitor.monitor(events)
            self.assertEqual(len(alerts), 1)
            print("✓ Test 10 passed: Load from file")
        finally:
            os.unlink(temp_path)
    
    def test_timestamp_formats(self):
        """Test Case 11: Handle different timestamp formats"""
        events = [
            {"service": "format", "timestamp": "2025-08-04T10:00:00Z"},
            {"service": "format", "timestamp": "2025-08-04T10:01:00+00:00"},
            {"service": "format", "timestamp": "2025-08-04T10:02:00Z"},
        ]
        
        valid_events = [e for e in events if self.monitor.validate_event(e)]
        self.assertEqual(len(valid_events), 3)
        print("✓ Test 11 passed: Timestamp formats")
    
    def test_initialization_validation(self):
        """Test Case 12: Validate initialization parameters"""
        with self.assertRaises(ValueError):
            HeartbeatMonitor(expected_interval_seconds=0, allowed_misses=3)
        
        with self.assertRaises(ValueError):
            HeartbeatMonitor(expected_interval_seconds=60, allowed_misses=-1)
        
        print("✓ Test 12 passed: Initialization validation")


def run_tests():
    """Run all tests with detailed output"""
    print("=" * 70)
    print("HEARTBEAT MONITORING SYSTEM - TEST SUITE")
    print("=" * 70)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestHeartbeatMonitor)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)