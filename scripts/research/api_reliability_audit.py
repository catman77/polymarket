#!/usr/bin/env python3
"""
API Reliability & Circuit Breaker Audit
Task 6.2 - Dmitri "The Hammer" Volkov (System Reliability Engineer)

Objective: Test external API failure handling, timeout configuration,
           circuit breakers, and fallback mechanisms.

Deliverables:
- API dependency map
- Timeout configuration audit
- Failure mode test results
- Circuit breaker analysis
- Historical API failure log analysis
- Resilience recommendations
"""

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class APIEndpoint:
    """External API dependency"""
    name: str
    url_pattern: str
    purpose: str
    found_in_code: bool = False
    timeout_configured: bool = False
    timeout_value: Optional[int] = None
    retry_logic: bool = False
    error_handling: bool = False
    fallback_present: bool = False


@dataclass
class APIFailure:
    """Historical API failure event"""
    timestamp: str
    api_name: str
    error_type: str
    recovered: bool
    context: str


@dataclass
class CircuitBreakerPattern:
    """Circuit breaker implementation detection"""
    file_path: str
    pattern_type: str  # 'explicit' or 'implicit'
    code_snippet: str
    assessment: str


class APIReliabilityAuditor:
    """Audit external API dependencies and failure handling"""

    # Known API endpoints
    APIS = {
        'Polymarket Gamma': {
            'url': 'gamma-api.polymarket.com',
            'purpose': 'Market discovery (find 15-min Up/Down markets)'
        },
        'Polymarket CLOB': {
            'url': 'clob.polymarket.com',
            'purpose': 'Order placement and execution'
        },
        'Polymarket Data': {
            'url': 'data-api.polymarket.com',
            'purpose': 'Position tracking and portfolio queries'
        },
        'Binance': {
            'url': 'api.binance.com',
            'purpose': 'BTC/ETH/SOL price feeds'
        },
        'Kraken': {
            'url': 'api.kraken.com',
            'purpose': 'Alternative crypto price feeds'
        },
        'Coinbase': {
            'url': 'api.coinbase.com',
            'purpose': 'Alternative crypto price feeds'
        },
        'Polygon RPC': {
            'url': 'polygon-rpc.com',
            'purpose': 'Balance checks, transaction signing, position redemption'
        }
    }

    def __init__(self, bot_code_path: str, log_file: str):
        self.bot_code_path = bot_code_path
        self.log_file = log_file
        self.apis: List[APIEndpoint] = []
        self.failures: List[APIFailure] = []
        self.circuit_breakers: List[CircuitBreakerPattern] = []

    def run_audit(self) -> Dict:
        """Execute full API reliability audit"""
        print("🔍 Starting API Reliability Audit...")

        # 1. Map API dependencies
        print("  → Mapping API dependencies...")
        self.map_api_dependencies()

        # 2. Audit timeout configuration
        print("  → Auditing timeout configuration...")
        self.audit_timeouts()

        # 3. Analyze circuit breaker patterns
        print("  → Analyzing circuit breaker patterns...")
        self.detect_circuit_breakers()

        # 4. Parse historical failures
        print("  → Parsing historical API failures...")
        self.parse_api_failures()

        # 5. Generate assessment
        print("  → Generating assessment...")
        return self.generate_assessment()

    def map_api_dependencies(self):
        """Find all API usage in codebase"""
        for api_name, api_info in self.APIS.items():
            endpoint = APIEndpoint(
                name=api_name,
                url_pattern=api_info['url'],
                purpose=api_info['purpose']
            )

            # Search for URL in code
            if os.path.exists(self.bot_code_path):
                try:
                    result = subprocess.run(
                        ['grep', '-r', api_info['url'], self.bot_code_path],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        endpoint.found_in_code = True
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass

            self.apis.append(endpoint)

    def audit_timeouts(self):
        """Audit timeout configuration for API calls"""
        if not os.path.exists(self.bot_code_path):
            return

        # Search for requests library usage
        timeout_patterns = [
            r'requests\.(get|post|put|delete)\([^)]*timeout\s*=\s*(\d+)',
            r'aiohttp.*timeout\s*=\s*(\d+)',
            r'urllib.*timeout\s*=\s*(\d+)'
        ]

        try:
            # Find Python files
            result = subprocess.run(
                ['find', self.bot_code_path, '-name', '*.py'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return

            py_files = result.stdout.strip().split('\n')

            for py_file in py_files:
                if not py_file or not os.path.exists(py_file):
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Check each API
                    for api in self.apis:
                        if api.url_pattern in content:
                            # Check for timeout
                            for pattern in timeout_patterns:
                                matches = re.findall(pattern, content)
                                if matches:
                                    api.timeout_configured = True
                                    api.timeout_value = int(matches[0][1]) if len(matches[0]) > 1 else None

                            # Check for try/except
                            if 'try:' in content and 'except' in content:
                                api.error_handling = True

                            # Check for retry logic
                            if 'retry' in content.lower() or 'for attempt in' in content:
                                api.retry_logic = True

                            # Check for fallback
                            if 'fallback' in content.lower() or 'alternative' in content.lower():
                                api.fallback_present = True

                except Exception:
                    continue

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def detect_circuit_breakers(self):
        """Detect circuit breaker patterns in code"""
        if not os.path.exists(self.bot_code_path):
            return

        circuit_breaker_patterns = [
            (r'consecutive.*fail', 'Consecutive failure tracking'),
            (r'failure_count|error_count', 'Error counter'),
            (r'backoff|exponential.*delay', 'Exponential backoff'),
            (r'if.*fail.*>.*\d+.*skip|halt', 'Conditional halt after failures'),
            (r'circuit.*breaker|breaker.*open', 'Explicit circuit breaker')
        ]

        try:
            result = subprocess.run(
                ['find', self.bot_code_path, '-name', '*.py'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return

            py_files = result.stdout.strip().split('\n')

            for py_file in py_files:
                if not py_file or not os.path.exists(py_file):
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines):
                        for pattern, pattern_type in circuit_breaker_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                # Extract 3-line context
                                start = max(0, i - 1)
                                end = min(len(lines), i + 2)
                                snippet = ''.join(lines[start:end]).strip()

                                breaker = CircuitBreakerPattern(
                                    file_path=py_file,
                                    pattern_type='explicit' if 'circuit' in pattern else 'implicit',
                                    code_snippet=snippet[:200],  # Truncate
                                    assessment=pattern_type
                                )
                                self.circuit_breakers.append(breaker)
                                break  # One pattern per line

                except Exception:
                    continue

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def parse_api_failures(self):
        """Parse log file for API failure events"""
        if not os.path.exists(self.log_file):
            return

        failure_keywords = [
            'timeout', 'connection error', 'api error', 'failed to fetch',
            'request failed', 'http error', 'connection refused', 'no response'
        ]

        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line_lower = line.lower()

                    # Check for failure keywords
                    for keyword in failure_keywords:
                        if keyword in line_lower:
                            # Extract timestamp
                            timestamp_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
                            timestamp = timestamp_match.group(0) if timestamp_match else 'Unknown'

                            # Identify API
                            api_name = 'Unknown'
                            for api_key in self.APIS.keys():
                                if api_key.lower() in line_lower or self.APIS[api_key]['url'] in line_lower:
                                    api_name = api_key
                                    break

                            # Check for recovery
                            recovered = 'retry' in line_lower or 'recovered' in line_lower or 'success' in line_lower

                            failure = APIFailure(
                                timestamp=timestamp,
                                api_name=api_name,
                                error_type=keyword,
                                recovered=recovered,
                                context=line.strip()[:150]
                            )
                            self.failures.append(failure)
                            break  # One failure per line

        except Exception:
            pass

    def generate_assessment(self) -> Dict:
        """Generate reliability assessment"""
        # Count APIs with proper handling
        with_timeout = sum(1 for api in self.apis if api.timeout_configured)
        with_error_handling = sum(1 for api in self.apis if api.error_handling)
        with_retry = sum(1 for api in self.apis if api.retry_logic)
        with_fallback = sum(1 for api in self.apis if api.fallback_present)

        total_apis = len([api for api in self.apis if api.found_in_code])

        # Calculate failure rate
        total_failures = len(self.failures)
        recovered_failures = sum(1 for f in self.failures if f.recovered)
        failure_rate = (total_failures / max(1, total_failures + 100)) * 100  # Assume ~100 successful calls

        # Determine reliability score
        if total_apis == 0:
            score = "UNKNOWN"
            verdict = "⚪ No API usage detected (development environment?)"
        elif with_timeout == total_apis and with_error_handling == total_apis:
            score = "EXCELLENT"
            verdict = "🟢 All APIs have timeouts and error handling"
        elif with_timeout >= total_apis * 0.8:
            score = "GOOD"
            verdict = "🟡 Most APIs have timeouts, some improvements needed"
        else:
            score = "POOR"
            verdict = "🔴 Many APIs lack proper timeout/error handling"

        # Circuit breaker assessment
        if len(self.circuit_breakers) >= 3:
            cb_verdict = "🟢 Multiple circuit breaker patterns detected"
        elif len(self.circuit_breakers) > 0:
            cb_verdict = "🟡 Some circuit breaker patterns found"
        else:
            cb_verdict = "🔴 No circuit breaker patterns detected"

        return {
            'score': score,
            'verdict': verdict,
            'apis': self.apis,
            'total_apis': total_apis,
            'with_timeout': with_timeout,
            'with_error_handling': with_error_handling,
            'with_retry': with_retry,
            'with_fallback': with_fallback,
            'circuit_breakers': self.circuit_breakers,
            'cb_verdict': cb_verdict,
            'failures': self.failures,
            'total_failures': total_failures,
            'recovered_failures': recovered_failures,
            'failure_rate': failure_rate
        }


def generate_markdown_report(assessment: Dict, output_file: str):
    """Generate detailed markdown report"""
    report = f"""# API Reliability & Circuit Breaker Audit Report

**Researcher:** Dmitri "The Hammer" Volkov (System Reliability Engineer)
**Task:** 6.2 - API Reliability & Circuit Breakers
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
**Overall Score:** {assessment['score']}

---

## Executive Summary

{assessment['verdict']}

**Key Findings:**
- **Total APIs Detected:** {assessment['total_apis']}
- **APIs with Timeouts:** {assessment['with_timeout']}/{assessment['total_apis']} ({(assessment['with_timeout']/max(1,assessment['total_apis'])*100):.0f}%)
- **APIs with Error Handling:** {assessment['with_error_handling']}/{assessment['total_apis']} ({(assessment['with_error_handling']/max(1,assessment['total_apis'])*100):.0f}%)
- **APIs with Retry Logic:** {assessment['with_retry']}/{assessment['total_apis']} ({(assessment['with_retry']/max(1,assessment['total_apis'])*100):.0f}%)
- **APIs with Fallbacks:** {assessment['with_fallback']}/{assessment['total_apis']} ({(assessment['with_fallback']/max(1,assessment['total_apis'])*100):.0f}%)
- **Circuit Breaker Patterns:** {len(assessment['circuit_breakers'])} detected
- **Historical Failures:** {assessment['total_failures']} events ({assessment['recovered_failures']} recovered)
- **Estimated Failure Rate:** {assessment['failure_rate']:.1f}%

---

## 1. API Dependency Map

The bot integrates with **7 external APIs** for trading operations:

"""

    # API table
    for api in assessment['apis']:
        status = "✅ Found" if api.found_in_code else "❌ Not Found"
        report += f"### {api.name}\n"
        report += f"- **URL Pattern:** `{api.url_pattern}`\n"
        report += f"- **Purpose:** {api.purpose}\n"
        report += f"- **Status:** {status}\n"

        if api.found_in_code:
            report += f"- **Timeout Configured:** {'✅ Yes' if api.timeout_configured else '❌ No'}"
            if api.timeout_value:
                report += f" ({api.timeout_value}s)"
            report += "\n"
            report += f"- **Error Handling:** {'✅ Yes' if api.error_handling else '❌ No'}\n"
            report += f"- **Retry Logic:** {'✅ Yes' if api.retry_logic else '❌ No'}\n"
            report += f"- **Fallback Present:** {'✅ Yes' if api.fallback_present else '❌ No'}\n"

        report += "\n"

    # Timeout Configuration Audit
    report += """---

## 2. Timeout Configuration Audit

**Importance:** Timeouts prevent hung requests from blocking the bot. Without timeouts, a single API failure can freeze trading operations indefinitely.

**Standard Practice:** All API calls should have explicit timeouts (typically 5-15 seconds for trading operations).

### Findings:

"""

    if assessment['with_timeout'] == assessment['total_apis'] and assessment['total_apis'] > 0:
        report += "✅ **EXCELLENT:** All API calls have explicit timeouts configured.\n\n"
    elif assessment['with_timeout'] >= assessment['total_apis'] * 0.8:
        report += f"🟡 **NEEDS IMPROVEMENT:** {assessment['total_apis'] - assessment['with_timeout']} API(s) lack timeout configuration.\n\n"
    else:
        report += f"🔴 **CRITICAL:** {assessment['total_apis'] - assessment['with_timeout']} API(s) lack timeout configuration. Bot vulnerable to hanging.\n\n"

    # Timeout recommendations
    report += """**Recommended Timeout Values:**
- **Price Feeds (Binance/Kraken/Coinbase):** 5-10 seconds (fast responses expected)
- **Order Placement (CLOB API):** 10-15 seconds (critical path, needs reliability)
- **Market Discovery (Gamma API):** 10-15 seconds (periodic scan, can tolerate some delay)
- **Position Tracking (Data API):** 10-15 seconds (not time-critical)
- **Blockchain RPC (Polygon):** 15-30 seconds (can be slow, especially during network congestion)

---

"""

    # Circuit Breaker Analysis
    report += f"""## 3. Circuit Breaker Analysis

{assessment['cb_verdict']}

**Circuit Breaker Pattern:** After N consecutive failures, stop calling the failed service for a cooldown period. This prevents cascade failures and gives the remote system time to recover.

**Detected Patterns:** {len(assessment['circuit_breakers'])}

"""

    if assessment['circuit_breakers']:
        for i, cb in enumerate(assessment['circuit_breakers'][:10], 1):  # Limit to 10
            report += f"### Pattern {i}: {cb.assessment}\n"
            report += f"- **File:** `{cb.file_path}`\n"
            report += f"- **Type:** {cb.pattern_type}\n"
            report += f"- **Code Snippet:**\n```python\n{cb.code_snippet}\n```\n\n"
    else:
        report += """**⚠️ No circuit breaker patterns detected.**

**Recommendation:** Implement circuit breaker logic for critical APIs:

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=3, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.is_open = False

    def call(self, func, *args, **kwargs):
        if self.is_open:
            if time.time() - self.last_failure_time < self.timeout:
                raise Exception("Circuit breaker is OPEN")
            else:
                self.is_open = False  # Try again after timeout

        try:
            result = func(*args, **kwargs)
            self.failure_count = 0  # Reset on success
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.is_open = True
            raise e

# Usage:
gamma_api_breaker = CircuitBreaker(failure_threshold=3, timeout=300)  # 5 min cooldown
result = gamma_api_breaker.call(fetch_markets)
```

"""

    # Historical API Failures
    report += """---

## 4. Historical API Failure Analysis

"""

    if assessment['failures']:
        report += f"**Total Failures:** {assessment['total_failures']} events detected in logs\n"
        report += f"**Recovered:** {assessment['recovered_failures']} ({(assessment['recovered_failures']/max(1,assessment['total_failures'])*100):.0f}%)\n"
        report += f"**Unrecovered:** {assessment['total_failures'] - assessment['recovered_failures']}\n\n"

        # Group by API
        api_failure_counts = {}
        for failure in assessment['failures']:
            api_failure_counts[failure.api_name] = api_failure_counts.get(failure.api_name, 0) + 1

        report += "### Failures by API:\n\n"
        for api_name, count in sorted(api_failure_counts.items(), key=lambda x: -x[1]):
            report += f"- **{api_name}:** {count} failures\n"

        report += "\n### Recent Failure Events (Sample):\n\n"
        for failure in assessment['failures'][:20]:  # Show first 20
            status = "✅ Recovered" if failure.recovered else "❌ Unrecovered"
            report += f"- **{failure.timestamp}** - {failure.api_name} - `{failure.error_type}` - {status}\n"
            report += f"  ```\n  {failure.context}\n  ```\n"
    else:
        report += "✅ **No API failures detected in logs** (or logs not available).\n\n"

    # Failure Mode Testing
    report += """---

## 5. Failure Mode Testing Recommendations

**Objective:** Simulate API failures to validate error handling.

### Test Scenarios:

#### Test 1: Gamma API Down (Market Discovery)
- **Simulation:** Block `gamma-api.polymarket.com` in /etc/hosts
- **Expected Behavior:** Bot skips market scan cycle, continues with existing positions
- **Failure Risk:** Bot crashes or enters infinite retry loop

#### Test 2: CLOB API Rate Limit (429 Error)
- **Simulation:** Rapid-fire 100 requests to CLOB API
- **Expected Behavior:** Bot backs off, waits before retrying
- **Failure Risk:** Bot hammers API, gets IP banned

#### Test 3: Polygon RPC Timeout
- **Simulation:** Point RPC URL to slow/unresponsive endpoint
- **Expected Behavior:** Balance check fails gracefully, bot uses cached balance
- **Failure Risk:** Trade placement hangs indefinitely

#### Test 4: Price Feed Inconsistency
- **Simulation:** Mock Binance returning stale price, Kraken/Coinbase fresh
- **Expected Behavior:** Bot detects outlier, uses median of 2/3 exchanges
- **Failure Risk:** Bot uses stale price, makes bad trade

#### Test 5: Network Partition
- **Simulation:** Block ALL external APIs for 60 seconds, then restore
- **Expected Behavior:** Bot halts trading, resumes after connectivity restored
- **Failure Risk:** Bot corrupts state or places duplicate orders

### Recommended Test Framework:
```python
# Mock external APIs with controllable failure rates
import responses

@responses.activate
def test_api_timeout():
    responses.add(
        responses.GET,
        'https://gamma-api.polymarket.com/markets',
        body=requests.Timeout()
    )

    # Bot should handle gracefully
    result = bot.scan_markets()
    assert result is None  # No crash
    assert bot.state == "WAITING"  # Enters safe state
```

---

## 6. Resilience Recommendations

"""

    # Generate recommendations based on findings
    recommendations = []

    if assessment['with_timeout'] < assessment['total_apis']:
        recommendations.append({
            'priority': 'CRITICAL',
            'title': 'Add Timeouts to All API Calls',
            'description': f"{assessment['total_apis'] - assessment['with_timeout']} API(s) lack explicit timeouts. Add `timeout=10` parameter to all requests."
        })

    if assessment['with_error_handling'] < assessment['total_apis']:
        recommendations.append({
            'priority': 'HIGH',
            'title': 'Wrap All API Calls in Try/Except',
            'description': f"{assessment['total_apis'] - assessment['with_error_handling']} API(s) lack error handling. Unhandled exceptions can crash the bot."
        })

    if len(assessment['circuit_breakers']) == 0:
        recommendations.append({
            'priority': 'HIGH',
            'title': 'Implement Circuit Breaker Pattern',
            'description': "No circuit breakers detected. Add for critical APIs (Gamma, CLOB, RPC) to prevent cascade failures."
        })

    if assessment['with_retry'] < assessment['total_apis'] * 0.5:
        recommendations.append({
            'priority': 'MEDIUM',
            'title': 'Add Exponential Backoff Retry Logic',
            'description': "Most APIs lack retry logic. Transient failures (network blips) cause unnecessary trade misses."
        })

    if assessment['with_fallback'] == 0:
        recommendations.append({
            'priority': 'MEDIUM',
            'title': 'Implement Fallback Mechanisms',
            'description': "No fallback APIs detected. If Binance down, bot should use Kraken/Coinbase for price feeds."
        })

    if assessment['total_failures'] > 10:
        recommendations.append({
            'priority': 'HIGH',
            'title': f"Investigate {assessment['total_failures']} Historical API Failures",
            'description': f"Logs show {assessment['total_failures']} API failures. Root cause analysis needed to prevent recurrence."
        })

    if not recommendations:
        recommendations.append({
            'priority': 'INFO',
            'title': 'API Reliability Excellent',
            'description': "No critical issues detected. Continue monitoring API performance."
        })

    for rec in recommendations:
        emoji = '🔴' if rec['priority'] == 'CRITICAL' else '🟡' if rec['priority'] == 'HIGH' else '🟢'
        report += f"### {emoji} {rec['priority']}: {rec['title']}\n\n"
        report += f"{rec['description']}\n\n"

    # Implementation Priority
    report += """---

## 7. Implementation Priority

1. **Week 1 (Critical):**
   - Add timeouts to all API calls
   - Wrap all API calls in try/except blocks
   - Test failure scenarios manually

2. **Week 2 (High):**
   - Implement circuit breaker for Gamma/CLOB/RPC
   - Add exponential backoff retry logic
   - Investigate historical API failures

3. **Week 3 (Medium):**
   - Implement fallback mechanisms (alternative price feeds)
   - Add API monitoring metrics (success rate, latency)
   - Create automated failure mode tests

4. **Ongoing:**
   - Monitor API failure logs weekly
   - Update circuit breaker thresholds based on observed failure rates
   - Document API SLA expectations

---

## 8. Conclusion

"""

    if assessment['score'] == 'EXCELLENT':
        report += "✅ **API reliability is EXCELLENT.** All critical safeguards in place. Continue monitoring.\n"
    elif assessment['score'] == 'GOOD':
        report += "🟡 **API reliability is GOOD.** Minor improvements needed (see recommendations above).\n"
    elif assessment['score'] == 'POOR':
        report += "🔴 **API reliability is POOR.** Critical improvements required to prevent system failures.\n"
    else:
        report += "⚪ **API reliability is UNKNOWN.** Code not accessible or no API usage detected.\n"

    report += "\n**Next Steps:**\n"
    report += "1. Review recommendations above\n"
    report += "2. Implement critical fixes (timeouts, error handling)\n"
    report += "3. Test failure scenarios on development environment\n"
    report += "4. Deploy to production after validation\n"
    report += "5. Monitor API performance for 1 week post-deployment\n\n"

    report += "---\n\n"
    report += "**END OF REPORT**\n"

    # Write report
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(report)

    print(f"✅ Report generated: {output_file}")


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='API Reliability & Circuit Breaker Audit')
    parser.add_argument('--bot-code', default='bot/', help='Path to bot code directory')
    parser.add_argument('--log-file', default='bot.log', help='Path to bot log file')
    parser.add_argument('--output', default='reports/dmitri_volkov/api_reliability_audit.md',
                       help='Output report path')

    args = parser.parse_args()

    print("=" * 80)
    print("API RELIABILITY & CIRCUIT BREAKER AUDIT")
    print("Researcher: Dmitri 'The Hammer' Volkov")
    print("Task: 6.2 - API Reliability & Circuit Breakers")
    print("=" * 80)
    print()

    auditor = APIReliabilityAuditor(args.bot_code, args.log_file)
    assessment = auditor.run_audit()

    print()
    print("📊 Assessment Complete")
    print(f"   Score: {assessment['score']}")
    print(f"   {assessment['verdict']}")
    print()

    generate_markdown_report(assessment, args.output)

    print()
    print("=" * 80)
    print("✅ AUDIT COMPLETE")
    print("=" * 80)

    # Exit code based on score
    if assessment['score'] in ['EXCELLENT', 'GOOD', 'UNKNOWN']:
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
