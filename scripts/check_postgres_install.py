"""
Check PostgreSQL installation and service status.
Attempts multiple connection methods and provides diagnostic information.
"""
import socket
import sys
import os
import subprocess
from typing import Dict, Any

def check_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP port is open and accepting connections."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def check_postgres_service() -> Dict[str, Any]:
    """Check PostgreSQL service status and connection details."""
    results = {
        'port_open': False,
        'port_open_ipv4': False,
        'port_open_ipv6': False,
        'service_running': False,
        'psql_available': False,
        'psql_version': None,
        'pg_isready': None,
        'errors': []
    }
    
    # Check if port 5432 is open on various addresses
    results['port_open_ipv4'] = check_port_open('127.0.0.1', 5432)
    results['port_open_ipv6'] = check_port_open('::1', 5432)
    results['port_open'] = results['port_open_ipv4'] or results['port_open_ipv6']
    
    # Check if psql is available
    try:
        psql_version = subprocess.check_output(['psql', '--version'], 
                                             stderr=subprocess.STDOUT,
                                             text=True)
        results['psql_available'] = True
        results['psql_version'] = psql_version.strip()
    except Exception as e:
        results['errors'].append(f"psql not found: {e}")
    
    # Try pg_isready if available
    try:
        pg_ready = subprocess.check_output(['pg_isready', '-h', 'localhost'], 
                                         stderr=subprocess.STDOUT,
                                         text=True)
        results['pg_isready'] = pg_ready.strip()
    except Exception as e:
        results['errors'].append(f"pg_isready failed: {e}")
    
    # Check Windows service status
    if sys.platform == 'win32':
        try:
            service_check = subprocess.check_output(
                ['sc', 'query', 'postgresql'], 
                stderr=subprocess.STDOUT,
                text=True
            )
            results['service_running'] = 'RUNNING' in service_check
        except Exception as e:
            results['errors'].append(f"Service check failed: {e}")
    
    return results

def main():
    """Run checks and print results."""
    print("Checking PostgreSQL installation and service status...")
    print("=" * 60)
    
    results = check_postgres_service()
    
    print("\nConnection Status:")
    print(f"- Port 5432 open (IPv4): {'Yes' if results['port_open_ipv4'] else 'No'}")
    print(f"- Port 5432 open (IPv6): {'Yes' if results['port_open_ipv6'] else 'No'}")
    
    if results['psql_available']:
        print(f"\npsql version: {results['psql_version']}")
    
    if results['pg_isready']:
        print(f"\npg_isready: {results['pg_isready']}")
    
    if sys.platform == 'win32':
        status = "Running" if results['service_running'] else "Not running"
        print(f"\nPostgreSQL Service: {status}")
    
    if results['errors']:
        print("\nErrors/Warnings:")
        for err in results['errors']:
            print(f"- {err}")
            
    print("\nRecommendations:")
    if not results['port_open']:
        print("- PostgreSQL is not accepting connections on port 5432")
        print("  • Check if PostgreSQL service is running")
        print("  • Verify postgresql.conf allows connections (listen_addresses)")
        print("  • Check firewall settings")
    
    if not results['psql_available']:
        print("- psql command not found")
        print("  • Add PostgreSQL bin directory to PATH")
        print("  • Typical location: C:\\Program Files\\PostgreSQL\\<version>\\bin")
    
    if not any([results['port_open'], results['psql_available'], results['service_running']]):
        print("\nNo PostgreSQL installation detected. Please:")
        print("1. Install PostgreSQL from https://www.postgresql.org/download/")
        print("2. Add bin directory to PATH")
        print("3. Start the PostgreSQL service")

if __name__ == '__main__':
    main()