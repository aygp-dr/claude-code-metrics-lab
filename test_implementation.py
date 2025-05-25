#!/usr/bin/env python3
"""
Quick implementation test for the enhanced simulator
"""

import yaml
import sys
import os

def test_configuration():
    """Test that the configuration file is valid"""
    try:
        with open('config/simulator-config.yml', 'r') as f:
            config = yaml.safe_load(f)
        print("✅ Configuration file is valid YAML")
        
        # Check required sections
        required_sections = ['users', 'scenarios', 'model_distribution', 'costs_per_1k_tokens']
        for section in required_sections:
            if section in config:
                print(f"✅ Configuration has '{section}' section")
            else:
                print(f"❌ Configuration missing '{section}' section")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

def test_simulator_import():
    """Test that the simulator module can be imported"""
    try:
        sys.path.append('src')
        import metrics_simulator
        print("✅ Enhanced simulator module imports successfully")
        return True
    except Exception as e:
        print(f"❌ Simulator import failed: {e}")
        return False

def test_docker_files():
    """Test that Docker files exist"""
    docker_files = [
        'docker-compose.dev.yml',
        'docker/Dockerfile.simulator',
        'docker/Dockerfile.scenario-runner'
    ]
    
    all_exist = True
    for file_path in docker_files:
        if os.path.exists(file_path):
            print(f"✅ Docker file exists: {file_path}")
        else:
            print(f"❌ Docker file missing: {file_path}")
            all_exist = False
    
    return all_exist

def test_script_files():
    """Test that script files exist and are executable"""
    script_files = [
        'scripts/test_dashboard.py',
        'scripts/scenario_runner.py'
    ]
    
    all_exist = True
    for file_path in script_files:
        if os.path.exists(file_path):
            print(f"✅ Script exists: {file_path}")
            # Make executable
            os.chmod(file_path, 0o755)
        else:
            print(f"❌ Script missing: {file_path}")
            all_exist = False
    
    return all_exist

def test_makefile_commands():
    """Test that Makefile has the new commands"""
    try:
        with open('Makefile', 'r') as f:
            makefile_content = f.read()
        
        required_commands = [
            'simulate-enhanced',
            'dev-env',
            'test-scenarios',
            'test-dashboard'
        ]
        
        all_found = True
        for command in required_commands:
            if f"{command}:" in makefile_content:
                print(f"✅ Makefile has '{command}' command")
            else:
                print(f"❌ Makefile missing '{command}' command")
                all_found = False
        
        return all_found
    except Exception as e:
        print(f"❌ Makefile test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Enhanced Simulator Implementation")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("Simulator Import", test_simulator_import),
        ("Docker Files", test_docker_files),
        ("Script Files", test_script_files),
        ("Makefile Commands", test_makefile_commands)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Implementation is ready.")
        return True
    else:
        print("❌ Some tests failed. Please check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)