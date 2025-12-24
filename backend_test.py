#!/usr/bin/env python3
"""
Dr. Neuro Backend API Testing Suite
Tests all backend endpoints for the medical diagnosis game
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class DrNeuroAPITester:
    def __init__(self, base_url="https://medic-akinator.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.game_id = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
            
        if self.token and 'Authorization' not in test_headers:
            test_headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        self.log(f"Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}", "PASS")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}", "FAIL")
                self.log(f"   Response: {response.text[:200]}", "FAIL")
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })
                try:
                    return False, response.json()
                except:
                    return False, {"error": response.text}

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}", "ERROR")
            self.failed_tests.append({
                "test": name,
                "error": str(e)
            })
            return False, {"error": str(e)}

    def test_health_check(self):
        """Test basic health/connectivity"""
        self.log("=== HEALTH CHECK ===")
        return self.run_test("Health Check", "GET", "", 200)  # Root should return 200 with API message

    def test_specialties(self):
        """Test specialties endpoint"""
        self.log("=== SPECIALTIES ===")
        success, data = self.run_test("Get Specialties", "GET", "specialties", 200)
        if success and isinstance(data, list) and len(data) > 0:
            self.log(f"✅ Found {len(data)} specialties")
            return True
        else:
            self.log("❌ Specialties data invalid")
            return False

    def test_auth_registration(self):
        """Test user registration"""
        self.log("=== AUTHENTICATION ===")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_user = {
            "email": f"test_user_{timestamp}@example.com",
            "password": "TestPass123!",
            "name": f"Test User {timestamp}"
        }
        
        success, data = self.run_test(
            "User Registration", 
            "POST", 
            "auth/register", 
            200, 
            test_user
        )
        
        if success and 'token' in data and 'user' in data:
            self.token = data['token']
            self.user_id = data['user']['user_id']
            self.log(f"✅ Registered user: {self.user_id}")
            return True
        else:
            self.log("❌ Registration failed")
            return False

    def test_auth_login(self):
        """Test user login with existing credentials"""
        if not self.user_id:
            self.log("⚠️ Skipping login test - no registered user")
            return True
            
        # Try to login with a test user (this might fail if user doesn't exist)
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        success, data = self.run_test(
            "User Login", 
            "POST", 
            "auth/login", 
            401,  # Expect 401 for non-existent user
            login_data
        )
        return True  # This test is expected to fail

    def test_auth_me(self):
        """Test getting current user info"""
        if not self.token:
            self.log("⚠️ Skipping auth/me test - no token")
            return True
            
        success, data = self.run_test("Get Current User", "GET", "auth/me", 200)
        if success and 'user_id' in data:
            self.log(f"✅ Current user: {data.get('name', 'Unknown')}")
            return True
        return success

    def test_game_start(self):
        """Test starting a game"""
        self.log("=== GAME FLOW ===")
        game_data = {
            "specialty": "cardiology",
            "is_anonymous": False if self.token else True
        }
        
        success, data = self.run_test(
            "Start Game", 
            "POST", 
            "game/start", 
            200, 
            game_data
        )
        
        if success and 'game_id' in data:
            self.game_id = data['game_id']
            self.log(f"✅ Started game: {self.game_id}")
            return True
        return False

    def test_game_answer(self):
        """Test answering game questions"""
        if not self.game_id:
            self.log("⚠️ Skipping game answer test - no active game")
            return True
            
        answer_data = {
            "game_id": self.game_id,
            "answer": "yes"
        }
        
        success, data = self.run_test(
            "Answer Question", 
            "POST", 
            "game/answer", 
            200, 
            answer_data
        )
        
        if success:
            if data.get('game_completed'):
                self.log("✅ Game completed with answer")
            else:
                self.log("✅ Question answered, game continues")
            return True
        return False

    def test_game_hint(self):
        """Test getting AI hints"""
        if not self.game_id:
            self.log("⚠️ Skipping hint test - no active game")
            return True
            
        hint_data = {"game_id": self.game_id}
        
        success, data = self.run_test(
            "Get AI Hint", 
            "POST", 
            "game/hint", 
            200, 
            hint_data
        )
        
        if success and 'hint' in data:
            self.log(f"✅ Received hint: {data['hint'][:50]}...")
            return True
        return success

    def test_leaderboard(self):
        """Test leaderboard endpoint"""
        self.log("=== LEADERBOARD ===")
        success, data = self.run_test("Get Leaderboard", "GET", "leaderboard", 200)
        
        if success and isinstance(data, list):
            self.log(f"✅ Leaderboard has {len(data)} entries")
            return True
        return False

    def test_complete_game_flow(self):
        """Test a complete game from start to finish"""
        self.log("=== COMPLETE GAME FLOW ===")
        
        # Start a new game
        game_data = {
            "specialty": "neurology",
            "is_anonymous": True  # Test anonymous mode
        }
        
        success, data = self.run_test(
            "Start Anonymous Game", 
            "POST", 
            "game/start", 
            200, 
            game_data
        )
        
        if not success or 'game_id' not in data:
            return False
            
        test_game_id = data['game_id']
        self.log(f"✅ Started anonymous game: {test_game_id}")
        
        # Answer several questions to complete the game
        answers = ["yes", "no", "maybe", "yes", "no"]
        
        for i, answer in enumerate(answers):
            answer_data = {
                "game_id": test_game_id,
                "answer": answer
            }
            
            success, response = self.run_test(
                f"Answer Question {i+1}", 
                "POST", 
                "game/answer", 
                200, 
                answer_data
            )
            
            if not success:
                return False
                
            if response.get('game_completed'):
                self.log(f"✅ Game completed after {i+1} questions")
                return True
                
        self.log("⚠️ Game didn't complete after 5 questions")
        return True  # This is acceptable

    def run_all_tests(self):
        """Run all test suites"""
        self.log("🚀 Starting Dr. Neuro Backend API Tests")
        self.log(f"Testing against: {self.base_url}")
        
        test_results = []
        
        # Core functionality tests
        test_results.append(self.test_health_check())
        test_results.append(self.test_specialties())
        
        # Authentication tests
        test_results.append(self.test_auth_registration())
        test_results.append(self.test_auth_me())
        test_results.append(self.test_auth_login())
        
        # Game functionality tests
        test_results.append(self.test_game_start())
        test_results.append(self.test_game_answer())
        test_results.append(self.test_game_hint())
        
        # Additional tests
        test_results.append(self.test_leaderboard())
        test_results.append(self.test_complete_game_flow())
        
        # Print summary
        self.log("=" * 50)
        self.log(f"📊 TEST SUMMARY")
        self.log(f"Tests run: {self.tests_run}")
        self.log(f"Tests passed: {self.tests_passed}")
        self.log(f"Tests failed: {self.tests_run - self.tests_passed}")
        self.log(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for failure in self.failed_tests:
                self.log(f"  - {failure.get('test', 'Unknown')}: {failure.get('error', failure.get('response', 'Unknown error'))}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = DrNeuroAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        tester.log("Tests interrupted by user")
        return 1
    except Exception as e:
        tester.log(f"Test suite failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())