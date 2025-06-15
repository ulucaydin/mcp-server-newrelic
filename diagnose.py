#!/usr/bin/env python3
"""
Diagnostic and Auto-fix Tool for MCP Server
Automatically diagnoses and fixes common issues
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import shutil


class Diagnostic:
    """Diagnostic and repair tool"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.issues = []
        self.fixes_applied = []
        
    def run(self):
        """Run all diagnostics and apply fixes"""
        print("🔍 MCP Server Diagnostic Tool")
        print("=" * 60)
        
        # Run diagnostics
        self.check_environment()
        self.check_directory_structure()
        self.check_configuration_files()
        self.check_dependencies()
        self.check_credentials()
        self.check_services()
        
        # Report findings
        self.report_findings()
        
        # Apply fixes if requested
        if self.issues:
            if len(sys.argv) > 1 and sys.argv[1] == '--fix':
                print("\n🔧 Auto-fix mode enabled")
                self.apply_fixes()
            else:
                print("\n💡 Run with --fix to automatically fix issues:"
                      "\n   python3 diagnose.py --fix")
            
    def check_environment(self):
        """Check environment setup"""
        print("\n📋 Checking Environment...")
        
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 8):
            self.issues.append({
                'type': 'environment',
                'issue': 'Python version too old',
                'fix': 'upgrade_python',
                'details': f'Current: {python_version.major}.{python_version.minor}, Required: 3.8+'
            })
        else:
            print(f"   ✅ Python {python_version.major}.{python_version.minor} OK")
            
        # Check Go installation
        try:
            result = subprocess.run(['go', 'version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ Go installed: {result.stdout.strip()}")
            else:
                raise Exception()
        except:
            self.issues.append({
                'type': 'environment',
                'issue': 'Go not installed',
                'fix': 'install_go',
                'details': 'Go is required for Discovery Core'
            })
            
    def check_directory_structure(self):
        """Check required directories exist"""
        print("\n📁 Checking Directory Structure...")
        
        required_dirs = [
            'pkg/discovery',
            'pkg/interface/mcp',
            'cmd/server',
            'intelligence',
            'tests/fixtures',
            'docs',
            'logs',
            '.cache'
        ]
        
        for dir_path in required_dirs:
            full_path = self.root_dir / dir_path
            if not full_path.exists():
                self.issues.append({
                    'type': 'directory',
                    'issue': f'Missing directory: {dir_path}',
                    'fix': 'create_directory',
                    'path': dir_path
                })
            else:
                print(f"   ✅ {dir_path}")
                
    def check_configuration_files(self):
        """Check required configuration files"""
        print("\n⚙️  Checking Configuration Files...")
        
        required_files = {
            '.env.example': self.create_env_example,
            'go.mod': self.create_go_mod,
            'requirements.txt': self.create_requirements_txt,
            'pyproject.toml': self.create_pyproject_toml,
            'docker-compose.yml': self.create_docker_compose,
            'Makefile': None  # Already exists
        }
        
        for file_name, create_func in required_files.items():
            file_path = self.root_dir / file_name
            if not file_path.exists():
                if file_name == 'Makefile':
                    # Makefile should exist
                    continue
                self.issues.append({
                    'type': 'config',
                    'issue': f'Missing file: {file_name}',
                    'fix': 'create_config_file',
                    'file': file_name,
                    'create_func': create_func
                })
            else:
                print(f"   ✅ {file_name}")
                
    def check_dependencies(self):
        """Check Python and Go dependencies"""
        print("\n📦 Checking Dependencies...")
        
        # Check Python imports
        required_python_modules = [
            'numpy',
            'pandas',
            'scikit-learn',
            'grpcio',
            'prometheus_client',
            'pyyaml',
            'python-dotenv'
        ]
        
        missing_modules = []
        for module in required_python_modules:
            try:
                __import__(module.replace('-', '_'))
                print(f"   ✅ Python: {module}")
            except ImportError:
                missing_modules.append(module)
                
        if missing_modules:
            self.issues.append({
                'type': 'dependency',
                'issue': 'Missing Python modules',
                'fix': 'install_python_deps',
                'modules': missing_modules
            })
            
        # Check Go modules
        go_mod_path = self.root_dir / 'go.mod'
        if go_mod_path.exists():
            try:
                result = subprocess.run(
                    ['go', 'mod', 'verify'],
                    cwd=self.root_dir,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print("   ✅ Go modules verified")
                else:
                    self.issues.append({
                        'type': 'dependency',
                        'issue': 'Go module issues',
                        'fix': 'fix_go_modules',
                        'details': result.stderr
                    })
            except:
                pass
                
    def check_credentials(self):
        """Check New Relic credentials"""
        print("\n🔑 Checking Credentials...")
        
        env_file = self.root_dir / '.env'
        if not env_file.exists():
            self.issues.append({
                'type': 'credentials',
                'issue': 'Missing .env file',
                'fix': 'create_env_file'
            })
            return
            
        # Load and check credentials
        required_vars = [
            'NEW_RELIC_API_KEY',
            'NEW_RELIC_ACCOUNT_ID',
            'NEW_RELIC_LICENSE_KEY'
        ]
        
        env_vars = {}
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
                    
        for var in required_vars:
            if var not in env_vars or not env_vars[var]:
                self.issues.append({
                    'type': 'credentials',
                    'issue': f'Missing or empty: {var}',
                    'fix': 'update_credentials',
                    'var': var
                })
            else:
                # Mask the value for display
                masked = env_vars[var][:10] + '...' if len(env_vars[var]) > 10 else 'SET'
                print(f"   ✅ {var}: {masked}")
                
    def check_services(self):
        """Check if services are accessible"""
        print("\n🌐 Checking Services...")
        
        # Check New Relic API
        try:
            import urllib.request
            response = urllib.request.urlopen('https://api.newrelic.com', timeout=5)
            if response.status == 200:
                print("   ✅ New Relic API accessible")
        except:
            self.issues.append({
                'type': 'network',
                'issue': 'Cannot reach New Relic API',
                'fix': 'check_network',
                'details': 'Check internet connection and firewall'
            })
            
    def report_findings(self):
        """Report diagnostic findings"""
        print("\n" + "=" * 60)
        print("📊 DIAGNOSTIC REPORT")
        print("=" * 60)
        
        if not self.issues:
            print("\n✅ All checks passed! System is ready.")
        else:
            print(f"\n⚠️  Found {len(self.issues)} issue(s):\n")
            
            for i, issue in enumerate(self.issues, 1):
                print(f"{i}. {issue['issue']}")
                if 'details' in issue:
                    print(f"   Details: {issue['details']}")
                    
    def ask_user(self, question: str) -> bool:
        """Ask user a yes/no question"""
        response = input(f"\n{question} (y/n): ").lower().strip()
        return response == 'y'
        
    def apply_fixes(self):
        """Apply automatic fixes"""
        print("\n🔧 Applying Fixes...")
        
        for issue in self.issues:
            fix_method = getattr(self, f"fix_{issue['fix']}", None)
            if fix_method:
                try:
                    fix_method(issue)
                    self.fixes_applied.append(issue['issue'])
                    print(f"   ✅ Fixed: {issue['issue']}")
                except Exception as e:
                    print(f"   ❌ Failed to fix {issue['issue']}: {e}")
            else:
                print(f"   ⚠️  No automatic fix for: {issue['issue']}")
                
        if self.fixes_applied:
            print(f"\n✅ Applied {len(self.fixes_applied)} fix(es)")
            print("\n🔄 Please run 'make test' to verify fixes")
            
    # Fix methods
    
    def fix_create_directory(self, issue: Dict):
        """Create missing directory"""
        path = self.root_dir / issue['path']
        path.mkdir(parents=True, exist_ok=True)
        
    def fix_create_config_file(self, issue: Dict):
        """Create missing configuration file"""
        if issue['create_func']:
            issue['create_func']()
            
    def fix_install_python_deps(self, issue: Dict):
        """Install missing Python dependencies"""
        modules = issue['modules']
        subprocess.run([sys.executable, '-m', 'pip', 'install'] + modules)
        
    def fix_fix_go_modules(self, issue: Dict):
        """Fix Go module issues"""
        subprocess.run(['go', 'mod', 'tidy'], cwd=self.root_dir)
        subprocess.run(['go', 'mod', 'download'], cwd=self.root_dir)
        
    # File creation methods
    
    def create_env_example(self):
        """Create .env.example from .env"""
        env_file = self.root_dir / '.env'
        example_file = self.root_dir / '.env.example'
        
        if env_file.exists():
            # Copy and sanitize
            with open(env_file) as f:
                lines = f.readlines()
                
            with open(example_file, 'w') as f:
                for line in lines:
                    if '=' in line and not line.strip().startswith('#'):
                        key = line.split('=')[0]
                        f.write(f"{key}=YOUR_{key.strip()}_HERE\n")
                    else:
                        f.write(line)
        else:
            # Create minimal example
            with open(example_file, 'w') as f:
                f.write("""# New Relic Configuration
NEW_RELIC_API_KEY=YOUR_API_KEY_HERE
NEW_RELIC_ACCOUNT_ID=YOUR_ACCOUNT_ID_HERE
NEW_RELIC_LICENSE_KEY=YOUR_LICENSE_KEY_HERE
NEW_RELIC_REGION=US

# Service Configuration
SERVER_PORT=8080
LOG_LEVEL=INFO
""")
                
    def create_go_mod(self):
        """Create go.mod file"""
        go_mod = self.root_dir / 'go.mod'
        with open(go_mod, 'w') as f:
            f.write("""module github.com/yourusername/mcp-server-newrelic

go 1.21

require (
    github.com/newrelic/go-agent/v3 v3.29.0
    google.golang.org/grpc v1.60.1
    go.opentelemetry.io/otel v1.21.0
)
""")
        # Run go mod tidy
        subprocess.run(['go', 'mod', 'tidy'], cwd=self.root_dir)
        
    def create_requirements_txt(self):
        """Create requirements.txt"""
        req_file = self.root_dir / 'requirements.txt'
        with open(req_file, 'w') as f:
            f.write("""# Core dependencies
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
scipy>=1.10.0

# New Relic
newrelic>=9.0.0

# API and server
grpcio>=1.60.0
grpcio-tools>=1.60.0
prometheus-client>=0.19.0
pyyaml>=6.0
python-dotenv>=1.0.0

# MCP
mcp>=0.1.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0

# Development
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
""")
            
    def create_pyproject_toml(self):
        """Create pyproject.toml"""
        pyproject = self.root_dir / 'pyproject.toml'
        with open(pyproject, 'w') as f:
            f.write("""[tool.poetry]
name = "mcp-server-newrelic"
version = "0.1.0"
description = "MCP Server for New Relic"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.8"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 100
target-version = ['py38']

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
""")
            
    def create_docker_compose(self):
        """Create docker-compose.yml"""
        compose_file = self.root_dir / 'docker-compose.yml'
        with open(compose_file, 'w') as f:
            f.write("""version: '3.8'

services:
  mcp-server:
    build: .
    ports:
      - "8080:8080"
      - "8081:8081"
    environment:
      - LOG_LEVEL=INFO
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./.cache:/app/.cache
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
""")


def main():
    """Main entry point"""
    diag = Diagnostic()
    diag.run()


if __name__ == "__main__":
    main()