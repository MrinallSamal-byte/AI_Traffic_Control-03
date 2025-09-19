#!/usr/bin/env python3
"""
Security Scanner - SQL injection tests and input sanitization
"""

import requests
import json
import time
import logging
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityScanner:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.vulnerabilities = []
        
    def authenticate(self, email="admin@example.com", password="admin123"):
        """Authenticate to get JWT token"""
        try:
            response = self.session.post(
                urljoin(self.base_url, "/api/v1/auth/login"),
                json={"email": email, "password": password}
            )
            
            if response.status_code == 200:
                token = response.json().get('access_token')
                self.session.headers.update({'Authorization': f'Bearer {token}'})
                logger.info("Authentication successful")
                return True
            else:
                logger.error("Authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        logger.info("Testing SQL injection vulnerabilities...")
        
        # Common SQL injection payloads
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "1' OR 1=1 --",
            "admin'--",
            "' OR 1=1#",
            "') OR ('1'='1",
            "1; SELECT * FROM users",
        ]
        
        # Test endpoints
        test_endpoints = [
            ("/api/v1/vehicles/{}/telemetry", "GET"),
            ("/api/v1/vehicles/{}/score", "GET"),
            ("/api/v1/vehicles/{}/transactions", "GET"),
        ]
        
        for endpoint_template, method in test_endpoints:
            for payload in sql_payloads:
                try:
                    endpoint = endpoint_template.format(payload)
                    url = urljoin(self.base_url, endpoint)
                    
                    if method == "GET":
                        response = self.session.get(url)
                    elif method == "POST":
                        response = self.session.post(url, json={"test": payload})
                    
                    # Check for SQL error messages
                    if self._check_sql_error_indicators(response):
                        self.vulnerabilities.append({
                            'type': 'SQL Injection',
                            'endpoint': endpoint,
                            'payload': payload,
                            'response_code': response.status_code,
                            'severity': 'HIGH'
                        })
                        logger.warning(f"Potential SQL injection: {endpoint}")
                    
                    time.sleep(0.1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Error testing {endpoint}: {e}")
    
    def _check_sql_error_indicators(self, response):
        """Check response for SQL error indicators"""
        error_indicators = [
            "sql syntax",
            "mysql_fetch",
            "postgresql error",
            "ora-00",
            "microsoft ole db",
            "sqlite_",
            "psycopg2",
            "column doesn't exist",
            "table doesn't exist"
        ]
        
        response_text = response.text.lower()
        return any(indicator in response_text for indicator in error_indicators)
    
    def test_xss_vulnerabilities(self):
        """Test for Cross-Site Scripting vulnerabilities"""
        logger.info("Testing XSS vulnerabilities...")
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
        ]
        
        # Test registration endpoint
        for payload in xss_payloads:
            try:
                response = self.session.post(
                    urljoin(self.base_url, "/api/v1/auth/register"),
                    json={
                        "name": payload,
                        "email": f"test{time.time()}@example.com"
                    }
                )
                
                if payload in response.text:
                    self.vulnerabilities.append({
                        'type': 'XSS',
                        'endpoint': '/api/v1/auth/register',
                        'payload': payload,
                        'severity': 'MEDIUM'
                    })
                    logger.warning("Potential XSS vulnerability in registration")
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error testing XSS: {e}")
    
    def test_authentication_bypass(self):
        """Test for authentication bypass vulnerabilities"""
        logger.info("Testing authentication bypass...")
        
        # Test endpoints without authentication
        protected_endpoints = [
            "/api/v1/vehicles",
            "/api/v1/admin/dashboard",
            "/api/v1/admin/alerts"
        ]
        
        # Remove auth header temporarily
        auth_header = self.session.headers.pop('Authorization', None)
        
        for endpoint in protected_endpoints:
            try:
                response = self.session.get(urljoin(self.base_url, endpoint))
                
                if response.status_code == 200:
                    self.vulnerabilities.append({
                        'type': 'Authentication Bypass',
                        'endpoint': endpoint,
                        'severity': 'HIGH'
                    })
                    logger.warning(f"Authentication bypass: {endpoint}")
                
            except Exception as e:
                logger.error(f"Error testing auth bypass: {e}")
        
        # Restore auth header
        if auth_header:
            self.session.headers['Authorization'] = auth_header
    
    def test_input_validation(self):
        """Test input validation"""
        logger.info("Testing input validation...")
        
        # Test with invalid data types
        invalid_inputs = [
            {"registration_no": 12345, "obu_device_id": None},  # Wrong types
            {"registration_no": "A" * 1000, "obu_device_id": "B" * 1000},  # Too long
            {"registration_no": "", "obu_device_id": ""},  # Empty strings
            {"registration_no": "../../../etc/passwd", "obu_device_id": "test"},  # Path traversal
        ]
        
        for invalid_input in invalid_inputs:
            try:
                response = self.session.post(
                    urljoin(self.base_url, "/api/v1/devices/register"),
                    json=invalid_input
                )
                
                # Should return 400 for invalid input
                if response.status_code not in [400, 422]:
                    self.vulnerabilities.append({
                        'type': 'Input Validation',
                        'endpoint': '/api/v1/devices/register',
                        'payload': str(invalid_input),
                        'severity': 'MEDIUM'
                    })
                    logger.warning("Weak input validation detected")
                
            except Exception as e:
                logger.error(f"Error testing input validation: {e}")
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        logger.info("Testing rate limiting...")
        
        endpoint = urljoin(self.base_url, "/api/v1/vehicles")
        
        # Send rapid requests
        for i in range(150):  # Exceed typical rate limits
            try:
                response = self.session.get(endpoint)
                
                if response.status_code == 429:
                    logger.info("Rate limiting is working")
                    return
                
            except Exception as e:
                logger.error(f"Error testing rate limiting: {e}")
                break
        
        # If we get here, rate limiting might not be working
        self.vulnerabilities.append({
            'type': 'Rate Limiting',
            'endpoint': '/api/v1/vehicles',
            'severity': 'LOW',
            'description': 'No rate limiting detected'
        })
    
    def run_full_scan(self):
        """Run complete security scan"""
        logger.info("Starting security scan...")
        
        if not self.authenticate():
            logger.error("Cannot proceed without authentication")
            return
        
        self.test_sql_injection()
        self.test_xss_vulnerabilities()
        self.test_authentication_bypass()
        self.test_input_validation()
        self.test_rate_limiting()
        
        self.generate_report()
    
    def generate_report(self):
        """Generate security scan report"""
        logger.info("Generating security report...")
        
        report = {
            'scan_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_vulnerabilities': len(self.vulnerabilities),
            'vulnerabilities_by_severity': {
                'HIGH': len([v for v in self.vulnerabilities if v.get('severity') == 'HIGH']),
                'MEDIUM': len([v for v in self.vulnerabilities if v.get('severity') == 'MEDIUM']),
                'LOW': len([v for v in self.vulnerabilities if v.get('severity') == 'LOW'])
            },
            'vulnerabilities': self.vulnerabilities
        }
        
        # Save report
        with open('security_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*50)
        print("SECURITY SCAN REPORT")
        print("="*50)
        print(f"Total Vulnerabilities: {report['total_vulnerabilities']}")
        print(f"High Severity: {report['vulnerabilities_by_severity']['HIGH']}")
        print(f"Medium Severity: {report['vulnerabilities_by_severity']['MEDIUM']}")
        print(f"Low Severity: {report['vulnerabilities_by_severity']['LOW']}")
        print("\nDetailed report saved to: security_report.json")
        print("="*50)

def main():
    scanner = SecurityScanner()
    scanner.run_full_scan()

if __name__ == "__main__":
    main()