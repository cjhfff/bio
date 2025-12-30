"""
诊断脚本：检查网络连接、代理设置和 DeepSeek API 密钥有效性
"""
import os
import sys
import time
import requests
from openai import OpenAI
from typing import Dict, List

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 禁用代理（确保测试准确）
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('all_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)

def check_network_connectivity() -> Dict[str, bool]:
    """检查网络连接"""
    print("=" * 80)
    print("1. 检查网络连接")
    print("=" * 80)
    
    results = {}
    
    # 检查基本网络连接
    test_urls = {
        "百度": "https://www.baidu.com",
        "Google": "https://www.google.com",
        "DeepSeek API": "https://api.deepseek.com",
    }
    
    for name, url in test_urls.items():
        try:
            response = requests.get(url, timeout=10, proxies={'http': None, 'https': None})
            results[name] = response.status_code == 200
            status = "✅ 连接成功" if results[name] else f"❌ 状态码: {response.status_code}"
            print(f"  {name:15s} {status}")
        except requests.exceptions.Timeout:
            results[name] = False
            print(f"  {name:15s} ❌ 连接超时")
        except requests.exceptions.ConnectionError as e:
            results[name] = False
            print(f"  {name:15s} ❌ 连接错误: {str(e)[:50]}")
        except Exception as e:
            results[name] = False
            print(f"  {name:15s} ❌ 未知错误: {type(e).__name__}")
    
    return results


def check_proxy_settings() -> Dict[str, str]:
    """检查代理设置"""
    print("\n" + "=" * 80)
    print("2. 检查代理设置")
    print("=" * 80)
    
    proxy_vars = [
        'http_proxy', 'https_proxy', 'all_proxy',
        'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY'
    ]
    
    proxy_settings = {}
    for var in proxy_vars:
        value = os.environ.get(var, '')
        proxy_settings[var] = value
        if value:
            print(f"  ⚠️  {var:15s} = {value}")
        else:
            print(f"  ✅ {var:15s} = (未设置)")
    
    return proxy_settings


def test_deepseek_api(api_key: str) -> Dict[str, any]:
    """测试 DeepSeek API 密钥"""
    print("\n" + "=" * 80)
    print("3. 测试 DeepSeek API 密钥")
    print("=" * 80)
    
    if not api_key:
        print("  ❌ API 密钥为空")
        return {"valid": False, "error": "API密钥为空"}
    
    # 显示密钥前8位和后4位（保护隐私）
    masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
    print(f"  测试密钥: {masked_key}")
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=60.0,
        max_retries=0  # 禁用自动重试，手动控制
    )
    
    # 测试简单请求
    test_messages = [
        {"role": "system", "content": "你是一个测试助手。"},
        {"role": "user", "content": "请回复'测试成功'"}
    ]
    
    try:
        print("  正在发送测试请求...")
        start_time = time.time()
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=test_messages,
            temperature=0.5,
            max_tokens=50,
            timeout=60.0
        )
        
        elapsed_time = time.time() - start_time
        
        if response.choices and response.choices[0].message:
            content = response.choices[0].message.content
            print(f"  ✅ API 密钥有效")
            print(f"  ✅ 响应时间: {elapsed_time:.2f} 秒")
            print(f"  ✅ 响应内容: {content[:50]}")
            
            # 检查使用情况
            if hasattr(response, 'usage'):
                usage = response.usage
                print(f"  📊 Token使用: 输入={usage.prompt_tokens}, 输出={usage.completion_tokens}, 总计={usage.total_tokens}")
            
            return {
                "valid": True,
                "response_time": elapsed_time,
                "content": content,
                "usage": response.usage.__dict__ if hasattr(response, 'usage') else None
            }
        else:
            print("  ⚠️  API 响应格式异常")
            return {"valid": False, "error": "响应格式异常"}
            
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"  ❌ API 调用失败: {error_type}")
        print(f"  ❌ 错误详情: {error_msg[:200]}")
        
        # 分析错误类型
        if "401" in error_msg or "Unauthorized" in error_msg:
            print("  💡 提示: API 密钥可能无效或已过期")
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            print("  💡 提示: API 调用频率超限，请稍后重试")
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            print("  💡 提示: 请求超时，可能是网络问题")
        elif "connection" in error_msg.lower():
            print("  💡 提示: 连接错误，请检查网络或代理设置")
        
        return {"valid": False, "error": error_msg, "error_type": error_type}


def check_backup_api_keys() -> List[str]:
    """检查是否有备用 API 密钥"""
    print("\n" + "=" * 80)
    print("4. 检查备用 API 密钥配置")
    print("=" * 80)
    
    # 从配置类读取（包括硬编码的备用密钥）
    try:
        from app.config import Config
        all_keys = Config.get_all_api_keys()
        backup_keys = Config.get_backup_api_keys()
        
        # 显示主密钥
        main_key = all_keys[0] if all_keys else ""
        if main_key:
            print(f"  ✅ 主密钥已配置: {main_key[:8]}...{main_key[-4:]}")
        else:
            print("  ⚠️  主密钥未配置")
        
        # 显示备用密钥
        if backup_keys:
            print(f"  ✅ 发现 {len(backup_keys)} 个备用 API 密钥:")
            for i, key in enumerate(backup_keys, 1):
                print(f"     备用密钥{i}: {key[:8]}...{key[-4:]}")
        else:
            print("  ⚠️  未配置备用 API 密钥")
            print("  💡 建议: 在环境变量中设置 DEEPSEEK_API_KEY_1, DEEPSEEK_API_KEY_2 等作为备用")
        
        return all_keys
    except Exception as e:
        print(f"  ❌ 无法读取配置: {e}")
        return []


def test_all_api_keys(api_keys: List[str]) -> Dict[str, Dict]:
    """测试所有 API 密钥"""
    if len(api_keys) <= 1:
        return {}
    
    print("\n" + "=" * 80)
    print("5. 测试所有备用 API 密钥")
    print("=" * 80)
    
    results = {}
    for i, key in enumerate(api_keys, 1):
        key_name = "主密钥" if i == 1 else f"备用密钥{i-1}"
        print(f"\n  测试 {key_name}...")
        result = test_deepseek_api(key)
        results[key_name] = result
        time.sleep(1)  # 避免请求过快
    
    return results


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("DeepSeek API 诊断工具")
    print("=" * 80)
    
    # 1. 检查网络连接
    network_results = check_network_connectivity()
    
    # 2. 检查代理设置
    proxy_settings = check_proxy_settings()
    
    # 3. 获取 API 密钥
    from app.config import Config
    api_key = Config.DEEPSEEK_API_KEY
    
    # 4. 测试 API 密钥
    api_result = test_deepseek_api(api_key)
    
    # 5. 检查备用密钥
    backup_keys = check_backup_api_keys()
    
    # 6. 如果有多于一个密钥，测试所有密钥
    if len(backup_keys) > 1:
        all_results = test_all_api_keys(backup_keys)
    
    # 总结
    print("\n" + "=" * 80)
    print("诊断总结")
    print("=" * 80)
    
    # 网络连接
    network_ok = all(network_results.values())
    print(f"网络连接: {'✅ 正常' if network_ok else '❌ 异常'}")
    
    # 代理设置
    has_proxy = any(proxy_settings.values())
    print(f"代理设置: {'⚠️  已设置代理' if has_proxy else '✅ 未设置代理（推荐）'}")
    
    # API 密钥
    api_ok = api_result.get("valid", False)
    print(f"API 密钥: {'✅ 有效' if api_ok else '❌ 无效或无法连接'}")
    
    if api_ok:
        response_time = api_result.get("response_time", 0)
        if response_time > 30:
            print(f"  ⚠️  响应时间较长: {response_time:.2f} 秒（可能影响正常使用）")
        else:
            print(f"  ✅ 响应时间正常: {response_time:.2f} 秒")
    
    # 建议
    print("\n" + "=" * 80)
    print("建议")
    print("=" * 80)
    
    if not network_ok:
        print("1. 网络连接异常，请检查网络设置或防火墙")
    
    if has_proxy:
        print("2. 检测到代理设置，如果 API 调用失败，请尝试禁用代理")
    
    if not api_ok:
        print("3. API 密钥无效或无法连接，请：")
        print("   - 检查 API 密钥是否正确")
        print("   - 检查账户余额是否充足")
        print("   - 检查网络连接是否正常")
        print("   - 考虑使用备用 API 密钥")
    
    if api_ok and api_result.get("response_time", 0) > 30:
        print("4. API 响应时间较长，建议：")
        print("   - 增加超时时间设置（已设置为300秒）")
        print("   - 检查网络延迟")
        print("   - 考虑使用备用 API 服务")
    
    print("\n诊断完成！\n")


if __name__ == "__main__":
    main()

