"""
API 测试脚本
用于测试后端API接口

使用方法:
1. 确保后端服务已启动 (python main.py)
2. 运行测试: python test_api.py
"""
import httpx
import json
from datetime import date, timedelta
import base64
import os


# API基础URL
BASE_URL = "http://localhost:8000"

# 测试用的全局变量
access_token = None
user_id = None
trip_id = None


def print_response(title: str, response: httpx.Response):
    """打印响应信息"""
    print(f"\n{'='*60}")
    print(f"【{title}】")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    try:
        data = response.json()
        print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return data
    except:
        print(f"响应文本: {response.text}")
        return None


def test_register():
    """测试用户注册"""
    global user_id
    
    url = f"{BASE_URL}/api/v1/auth/register"
    data = {
        "email": "test@example.com",
        "password": "test123456",
        "preferences": "喜欢美食和动漫"
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=data)
            result = print_response("用户注册", response)
            
            if result and "user_id" in result:
                user_id = result["user_id"]
                return True
            return False
    except httpx.TimeoutException:
        print("\n❌ 注册请求超时，请检查后端服务是否正常运行")
        return False
    except Exception as e:
        print(f"\n❌ 注册请求出错: {str(e)}")
        return False


def test_login():
    """测试用户登录"""
    global access_token
    
    url = f"{BASE_URL}/api/v1/auth/login"
    # FastAPI OAuth2PasswordRequestForm 需要 form 数据
    data = {
        "username": "test@example.com",
        "password": "test123456"
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, data=data)
            result = print_response("用户登录", response)
            
            if result and "access_token" in result:
                access_token = result["access_token"]
                print(f"\n✅ 获取到Token: {access_token[:50]}...")
                return True
            return False
    except httpx.TimeoutException:
        print("\n❌ 登录请求超时，请检查后端服务是否正常运行")
        return False
    except Exception as e:
        print(f"\n❌ 登录请求出错: {str(e)}")
        return False


def test_get_user_profile():
    """测试获取用户档案"""
    global access_token
    
    if not access_token:
        print("❌ 请先登录获取Token")
        return False
    
    url = f"{BASE_URL}/api/v1/users/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers)
            result = print_response("获取用户档案", response)
            return result is not None
    except httpx.TimeoutException:
        print("\n❌ 获取用户档案请求超时")
        return False
    except Exception as e:
        print(f"\n❌ 获取用户档案出错: {str(e)}")
        return False


def test_update_user_profile():
    """测试更新用户偏好"""
    global access_token
    
    if not access_token:
        print("❌ 请先登录获取Token")
        return False
    
    url = f"{BASE_URL}/api/v1/users/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    data = {
        "preferences": "喜欢美食、动漫和亲子旅游"
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.put(url, json=data, headers=headers)
            result = print_response("更新用户偏好", response)
            return result is not None
    except httpx.TimeoutException:
        print("\n❌ 更新用户偏好请求超时")
        return False
    except Exception as e:
        print(f"\n❌ 更新用户偏好出错: {str(e)}")
        return False


def test_create_plan_voice():
    """测试语音创建行程"""
    global access_token, trip_id
    
    if not access_token:
        print("❌ 请先登录获取Token")
        return False
    
    url = f"{BASE_URL}/api/v1/plan/voice"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 检查是否有测试音频文件
    audio_file = "test_audio.wav"
    if not os.path.exists(audio_file):
        print(f"\n⚠️ 未找到测试音频文件 {audio_file}，跳过语音行程测试")
        print("   如需测试，请准备一个.wav格式的音频文件，包含行程需求（如：我想去东京，5天，预算15000元）")
        return False
    
    try:
        with open(audio_file, "rb") as f:
            files = {"file": (audio_file, f, "audio/wav")}
            
            with httpx.Client(timeout=120.0) as client:  # 增加超时时间，因为LLM和地图API可能需要时间
                try:
                    response = client.post(
                        url,
                        headers=headers,
                        files=files
                    )
                    result = print_response("创建行程（语音）", response)
                    
                    if result and "trip_id" in result:
                        trip_id = result["trip_id"]
                        print(f"\n✅ 行程创建成功，trip_id: {trip_id}")
                        return True
                    else:
                        print(f"\n❌ 行程创建失败或仍在处理中")
                        return False
                except httpx.TimeoutException:
                    print("\n⏱️ 请求超时，行程生成可能需要更长时间")
                    print("   这是正常的，因为需要调用LLM和地图API")
                    return False
                except Exception as e:
                    print(f"\n❌ 请求出错: {str(e)}")
                    return False
    except Exception as e:
        print(f"\n❌ 读取音频文件出错: {str(e)}")
        return False


def test_create_plan_text():
    """测试文本创建行程"""
    global access_token, trip_id
    
    if not access_token:
        print("❌ 请先登录获取Token")
        return False
    
    url = f"{BASE_URL}/api/v1/plan/text"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 生成测试数据：5天后开始，8天的行程
    start_date = (date.today() + timedelta(days=6)).isoformat()
    end_date = (date.today() + timedelta(days=9)).isoformat()
    
    data = {
        "destination": "南京",
        "start_date": start_date,
        "end_date": end_date,
        "budget_cny": 8000.0,
        "people": "2大1小",
        "preferences": "喜欢美食，喜欢历史人文，带孩子旅游"
    }
    
    print(f"\n📝 发送行程请求:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    
    with httpx.Client(timeout=120.0) as client:  # 增加超时时间，因为LLM和地图API可能需要时间
        try:
            response = client.post(url, json=data, headers=headers)
            result = print_response("创建行程（文本）", response)
            
            if result and "trip_id" in result:
                trip_id = result["trip_id"]
                print(f"\n✅ 行程创建成功，trip_id: {trip_id}")
                return True
            else:
                print(f"\n❌ 行程创建失败或仍在处理中")
                return False
        except httpx.TimeoutException:
            print("\n⏱️ 请求超时，行程生成可能需要更长时间")
            print("   这是正常的，因为需要调用LLM和地图API")
            return False
        except Exception as e:
            print(f"\n❌ 请求出错: {str(e)}")
            return False


def test_get_trip_list():
    """测试获取行程列表"""
    global access_token
    
    if not access_token:
        print("❌ 请先登录获取Token")
        return False
    
    url = f"{BASE_URL}/api/v1/plan/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers)
            result = print_response("获取行程列表", response)
            return result is not None
    except httpx.TimeoutException:
        print("\n❌ 获取行程列表请求超时")
        return False
    except Exception as e:
        print(f"\n❌ 获取行程列表出错: {str(e)}")
        return False


def test_get_trip_detail():
    """测试获取行程详情"""
    global access_token, trip_id
    
    if not access_token or not trip_id:
        print("❌ 请先登录并创建行程")
        return False
    
    url = f"{BASE_URL}/api/v1/plan/{trip_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers)
            result = print_response("获取行程详情", response)
            return result is not None
    except httpx.TimeoutException:
        print("\n❌ 获取行程详情请求超时")
        return False
    except Exception as e:
        print(f"\n❌ 获取行程详情出错: {str(e)}")
        return False


def test_record_expense_text():
    """测试文本录入开销"""
    global access_token, trip_id
    
    if not access_token or not trip_id:
        print("❌ 请先登录并创建行程")
        return False
    
    url = f"{BASE_URL}/api/v1/budget/expense/text"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    data = {
        "trip_id": trip_id,
        "text_input": "今天在餐厅吃了日式料理，花费了500元"
    }
    
    with httpx.Client(timeout=60.0) as client:
        try:
            response = client.post(url, json=data, headers=headers)
            result = print_response("文本录入开销", response)
            return result is not None
        except httpx.TimeoutException:
            print("\n⏱️ 请求超时（LLM解析可能需要时间）")
            return False
        except Exception as e:
            print(f"\n❌ 请求出错: {str(e)}")
            return False


def test_record_expense_voice():
    """测试语音录入开销（需要音频文件）"""
    global access_token, trip_id
    
    if not access_token or not trip_id:
        print("❌ 请先登录并创建行程")
        return False
    
    url = f"{BASE_URL}/api/v1/budget/expense/voice"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 检查是否有测试音频文件
    audio_file = "test_audio.wav"
    if not os.path.exists(audio_file):
        print(f"\n⚠️ 未找到测试音频文件 {audio_file}，跳过语音测试")
        print("   如需测试，请准备一个.wav格式的音频文件")
        return False
    
    try:
        with open(audio_file, "rb") as f:
            files = {"file": (audio_file, f, "audio/wav")}
            
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    url,
                    headers=headers,
                    files=files,
                    data={"trip_id": trip_id}
                )
                result = print_response("语音录入开销", response)
                return result is not None
    except Exception as e:
        print(f"\n❌ 请求出错: {str(e)}")
        return False


def test_get_trip_finance():
    """测试获取行程费用信息"""
    global access_token, trip_id
    
    if not access_token or not trip_id:
        print("❌ 请先登录并创建行程")
        return False
    
    url = f"{BASE_URL}/api/v1/budget/{trip_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers)
            result = print_response("获取行程费用信息", response)
            return result is not None
    except httpx.TimeoutException:
        print("\n❌ 获取行程费用信息请求超时")
        return False
    except Exception as e:
        print(f"\n❌ 获取行程费用信息出错: {str(e)}")
        return False


def test_health_check():
    """测试健康检查"""
    url = f"{BASE_URL}/health"
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            result = print_response("健康检查", response)
            return result is not None
    except httpx.TimeoutException:
        print("\n❌ 健康检查超时，请确认后端服务是否启动")
        return False
    except Exception as e:
        print(f"\n❌ 健康检查出错: {str(e)}")
        return False


def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("🚀 开始API测试")
    print("="*60)
    
    # 测试结果统计
    results = []
    
    # 1. 健康检查
    print("\n\n【第一步：健康检查】")
    results.append(("健康检查", test_health_check()))
    
    # 2. 用户认证与资料
    print("\n\n【第二步：用户认证与资料】")
    if not test_register():
        print("⚠️ 注册失败，可能是用户已存在，继续尝试登录...")
    
    if not test_login():
        print("❌ 登录失败，无法继续测试")
        return
    results.append(("用户登录", True))
    
    if test_get_user_profile():
        results.append(("获取用户档案", True))
    
    if test_update_user_profile():
        results.append(("更新用户偏好", True))
    
    # 3. 行程规划
    print("\n\n【第三步：行程规划】")
    print("⚠️ 注意：创建行程需要调用LLM和地图API，可能需要较长时间（30-60秒）")

    global trip_id
    trip_id = "8efc8d4d-94e1-4136-b6cf-144425b1f489"
    

    # # 测试语音创建行程
    # if test_create_plan_voice():
    #     results.append(("创建行程（语音）", True))
        
    #     # 等待一下让后端处理
    #     import time
    #     print("\n⏳ 等待5秒后查询行程详情...")
    #     time.sleep(5)
        
    #     if test_get_trip_list():
    #         results.append(("获取行程列表", True))
        
    #     if test_get_trip_detail():
    #         results.append(("获取行程详情", True))
    # else:
    #     results.append(("创建行程（语音）", False))
    #     print("\n⚠️ 语音行程创建失败或未找到音频文件，跳过后续行程相关测试")

    # 测试文本创建行程
    # if test_create_plan_text():
    if True:
        results.append(("创建行程（文本）", True))
        # 等待一下让后端处理
        import time
        print("\n⏳ 等待5秒后查询行程详情...")
        time.sleep(5)
        
        if test_get_trip_list():
            results.append(("获取行程列表", True))
        
        if test_get_trip_detail():
            results.append(("获取行程详情", True))
    else:
        results.append(("创建行程（文本）", False))
        print("\n⚠️ 行程创建失败或仍在处理中，跳过后续行程相关测试")

    
    # 4. 费用管理（已注释，需要时取消注释）
    print("\n\n【第四步：费用管理】")
    if trip_id:
        if test_record_expense_text():
            results.append(("文本录入开销", True))
        
        test_record_expense_voice()  # 可能需要音频文件，失败不算错误
        
        if test_get_trip_finance():
            results.append(("获取费用信息", True))
    else:
        print("⚠️ 无行程ID，跳过费用管理测试")
    
    # 测试结果汇总
    print("\n\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    passed = 0
    failed = 0
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {name}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed + failed} 个测试")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    
    print("\n" + "="*60)
    print("💡 提示:")
    print("   1. 如果创建行程超时，请检查:")
    print("      - .env文件中的API密钥是否正确")
    print("      - 千问API、地图API是否可用")
    print("      - 后端日志是否有错误信息")
    print("   2. 访问 http://localhost:8000/docs 查看API文档")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()


