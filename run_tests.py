#!/usr/bin/env python3
"""
测试运行脚本
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(command: str, description: str = "") -> bool:
    """运行命令并返回是否成功"""
    if description:
        print(f"\n🔧 {description}")
    
    print(f"执行命令: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ 命令执行成功")
        if result.stdout:
            print("输出:", result.stdout)
        return True
    else:
        print("❌ 命令执行失败")
        if result.stderr:
            print("错误:", result.stderr)
        return False

def check_dependencies() -> bool:
    """检查测试依赖"""
    print("🔍 检查测试依赖...")
    
    required_packages = [
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "httpx",
        "fastapi"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements-dev.txt")
        return False
    
    print("✅ 所有依赖包已安装")
    return True

def run_unit_tests(verbose: bool = False, coverage: bool = False) -> bool:
    """运行单元测试"""
    print("\n🧪 运行单元测试...")
    
    # 设置环境变量
    env = os.environ.copy()
    env["TESTING"] = "true"
    env["DATABASE_URL"] = "sqlite:///./test.db"
    
    # 构建测试命令
    cmd_parts = ["python", "-m", "pytest", "tests/"]
    
    if verbose:
        cmd_parts.append("-v")
    
    if coverage:
        cmd_parts.extend([
            "--cov=muyugan_backend",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    cmd_parts.extend([
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])
    
    command = " ".join(cmd_parts)
    
    # 运行测试
    result = subprocess.run(command, shell=True, env=env)
    return result.returncode == 0

def run_integration_tests(verbose: bool = False) -> bool:
    """运行集成测试"""
    print("\n🔗 运行集成测试...")
    
    # 设置环境变量
    env = os.environ.copy()
    env["TESTING"] = "true"
    env["DATABASE_URL"] = "sqlite:///./test.db"
    
    # 构建测试命令
    cmd_parts = ["python", "-m", "pytest", "tests/", "-m", "integration"]
    
    if verbose:
        cmd_parts.append("-v")
    
    cmd_parts.extend([
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])
    
    command = " ".join(cmd_parts)
    
    # 运行测试
    result = subprocess.run(command, shell=True, env=env)
    return result.returncode == 0

def run_performance_tests(verbose: bool = False) -> bool:
    """运行性能测试"""
    print("\n⚡ 运行性能测试...")
    
    # 设置环境变量
    env = os.environ.copy()
    env["TESTING"] = "true"
    env["DATABASE_URL"] = "sqlite:///./test.db"
    
    # 构建测试命令
    cmd_parts = ["python", "-m", "pytest", "tests/", "-m", "performance"]
    
    if verbose:
        cmd_parts.append("-v")
    
    cmd_parts.extend([
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])
    
    command = " ".join(cmd_parts)
    
    # 运行测试
    result = subprocess.run(command, shell=True, env=env)
    return result.returncode == 0

def run_all_tests(verbose: bool = False, coverage: bool = False) -> bool:
    """运行所有测试"""
    print("\n🚀 运行所有测试...")
    
    # 设置环境变量
    env = os.environ.copy()
    env["TESTING"] = "true"
    env["DATABASE_URL"] = "sqlite:///./test.db"
    
    # 构建测试命令
    cmd_parts = ["python", "-m", "pytest", "tests/"]
    
    if verbose:
        cmd_parts.append("-v")
    
    if coverage:
        cmd_parts.extend([
            "--cov=muyugan_backend",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    cmd_parts.extend([
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])
    
    command = " ".join(cmd_parts)
    
    # 运行测试
    result = subprocess.run(command, shell=True, env=env)
    return result.returncode == 0

def generate_test_report() -> bool:
    """生成测试报告"""
    print("\n📊 生成测试报告...")
    
    # 检查是否有coverage数据
    if not Path(".coverage").exists():
        print("❌ 没有找到coverage数据，请先运行带coverage的测试")
        return False
    
    # 生成HTML报告
    command = "coverage html"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ 测试报告已生成到 htmlcov/ 目录")
        return True
    else:
        print("❌ 生成测试报告失败")
        if result.stderr:
            print("错误:", result.stderr)
        return False

def clean_test_files() -> bool:
    """清理测试文件"""
    print("\n🧹 清理测试文件...")
    
    test_files = [
        "test.db",
        ".coverage",
        "htmlcov/",
        ".pytest_cache/",
        "__pycache__/",
        "*.pyc"
    ]
    
    for file_pattern in test_files:
        if Path(file_pattern).exists():
            try:
                if Path(file_pattern).is_dir():
                    import shutil
                    shutil.rmtree(file_pattern)
                else:
                    Path(file_pattern).unlink()
                print(f"✅ 已删除: {file_pattern}")
            except Exception as e:
                print(f"⚠️ 删除失败 {file_pattern}: {e}")
    
    print("✅ 测试文件清理完成")
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Muyugan 后端系统测试运行器")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "performance", "all"], 
        default="all",
        help="测试类型 (默认: all)"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true",
        help="详细输出"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="生成覆盖率报告"
    )
    parser.add_argument(
        "--clean", 
        action="store_true",
        help="清理测试文件"
    )
    parser.add_argument(
        "--report", 
        action="store_true",
        help="生成测试报告"
    )
    
    args = parser.parse_args()
    
    print("🚀 Muyugan 后端系统测试运行器")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 清理测试文件
    if args.clean:
        clean_test_files()
        return
    
    # 生成测试报告
    if args.report:
        if generate_test_report():
            print("\n🎉 测试报告生成完成！")
        else:
            print("\n❌ 测试报告生成失败！")
        return
    
    # 运行测试
    success = False
    if args.type == "unit":
        success = run_unit_tests(args.verbose, args.coverage)
    elif args.type == "integration":
        success = run_integration_tests(args.verbose)
    elif args.type == "performance":
        success = run_performance_tests(args.verbose)
    elif args.type == "all":
        success = run_all_tests(args.verbose, args.coverage)
    
    # 输出结果
    if success:
        print("\n🎉 所有测试通过！")
        if args.coverage:
            print("📊 覆盖率报告已生成")
    else:
        print("\n❌ 测试失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()
