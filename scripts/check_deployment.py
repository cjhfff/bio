#!/usr/bin/env python3
"""
部署环境检查脚本
检查服务器部署所需的所有配置和依赖
"""
import os
import sys
from pathlib import Path

def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 版本过低，需要 Python 3.8+")
        return False
    print(f"✅ Python 版本: {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """检查依赖包"""
    required_packages = [
        'requests',
        'openai',
        'feedparser',
        'biopython',
        'python-dotenv',
        'fastapi',
        'uvicorn',
        'email-validator',
        'tiktoken'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (缺失)")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  缺失依赖: {', '.join(missing)}")
        print("   安装命令: pip install -r requirements.txt")
        return False
    return True

def check_directories():
    """检查必要目录"""
    dirs = ['data', 'logs', 'reports']
    all_ok = True
    
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if dir_path.exists() and dir_path.is_dir():
            # 检查写入权限
            test_file = dir_path / '.write_test'
            try:
                test_file.touch()
                test_file.unlink()
                print(f"✅ {dir_name}/ (存在且可写)")
            except Exception as e:
                print(f"❌ {dir_name}/ (无写入权限: {e})")
                all_ok = False
        else:
            print(f"⚠️  {dir_name}/ (不存在，将自动创建)")
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"✅ {dir_name}/ (已创建)")
            except Exception as e:
                print(f"❌ {dir_name}/ (创建失败: {e})")
                all_ok = False
    
    return all_ok

def check_env_file():
    """检查环境变量配置"""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("⚠️  .env 文件不存在")
        print("   请创建 .env 文件并配置必需项")
        return False
    
    print("✅ .env 文件存在")
    
    # 读取并检查必需配置
    required_vars = ['DEEPSEEK_API_KEY', 'PUBMED_EMAIL']
    missing_vars = []
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        for var in required_vars:
            value = os.getenv(var)
            if not value or value.strip() == '':
                missing_vars.append(var)
                print(f"❌ {var} (未配置)")
            else:
                # 隐藏敏感信息
                if 'KEY' in var or 'PASSWORD' in var:
                    masked = value[:8] + '...' if len(value) > 8 else '***'
                    print(f"✅ {var} = {masked}")
                else:
                    print(f"✅ {var} = {value}")
        
        if missing_vars:
            print(f"\n⚠️  缺失必需配置: {', '.join(missing_vars)}")
            return False
        
    except ImportError:
        print("⚠️  python-dotenv 未安装，无法读取 .env 文件")
        return False
    
    return True

def check_database():
    """检查数据库"""
    db_path = Path(os.getenv('DB_PATH', 'data/paper_push.db'))
    
    if db_path.exists():
        print(f"✅ 数据库文件存在: {db_path}")
        # 检查数据库是否可访问
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.execute("SELECT 1")
            conn.close()
            print("✅ 数据库可访问")
            return True
        except Exception as e:
            print(f"❌ 数据库访问失败: {e}")
            return False
    else:
        print(f"⚠️  数据库文件不存在: {db_path}")
        print("   将在首次运行时自动创建")
        return True  # 不是错误，只是未初始化

def check_network():
    """检查网络连接"""
    import urllib.request
    
    test_urls = [
        'https://api.deepseek.com',
        'https://www.ncbi.nlm.nih.gov',
        'https://api.github.com'
    ]
    
    print("\n检查网络连接...")
    all_ok = True
    
    for url in test_urls:
        try:
            urllib.request.urlopen(url, timeout=5)
            print(f"✅ {url}")
        except Exception as e:
            print(f"❌ {url} (连接失败: {e})")
            all_ok = False
    
    return all_ok

def check_proxy_settings():
    """检查代理设置"""
    proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
    has_proxy = False
    
    for var in proxy_vars:
        value = os.getenv(var)
        if value:
            has_proxy = True
            print(f"⚠️  检测到代理设置: {var} = {value}")
    
    if not has_proxy:
        print("✅ 未检测到代理设置（代码会清除代理，如需使用代理请修改代码）")
    
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("部署环境检查")
    print("=" * 60)
    print()
    
    checks = [
        ("Python 版本", check_python_version),
        ("依赖包", check_dependencies),
        ("目录结构", check_directories),
        ("环境配置", check_env_file),
        ("数据库", check_database),
        ("网络连接", check_network),
        ("代理设置", check_proxy_settings),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n【{name}】")
        print("-" * 40)
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ 检查失败: {e}")
            results.append((name, False))
    
    # 总结
    print("\n" + "=" * 60)
    print("检查总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 项检查通过")
    
    if passed == total:
        print("\n🎉 所有检查通过！系统已准备好部署。")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 项检查未通过，请修复后重试。")
        return 1

if __name__ == '__main__':
    sys.exit(main())

