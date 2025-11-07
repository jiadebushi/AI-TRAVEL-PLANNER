"""
异步API测试脚本
使用httpx异步客户端进行测试，适合高并发场景

使用方法:
1. 确保后端服务已启动 (python main.py)
2. 运行测试: python test_api_async.py
"""
import httpx
import json
import asyncio
from datetime import date, timedelta


BASE_URL = "http://localhost:8000"
access_token = None
trip_id = None


async def test_async_request(method: str, url: str, **kwargs):
    """异步HTTP请求"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        if method.upper() == "GET":
            return await client.get(url, **kwargs)
        elif method.upper() == "POST":
            return await client.post(url, **kwargs)
        elif method.upper() == "PUT":
            return await client.put(url, **kwargs)
        elif method.upper() == "DELETE":
            return await client.delete(url, **kwargs)


async def test_login_async():
    """异步登录测试"""
    global access_token
    
    url = f"{BASE_URL}/api/v1/auth/login"
    data = {
        "username": "test@example.com",
        "password": "test123456"
    }
    
    response = await test_async_request("POST", url, data=data)
    
    if response.status_code == 200:
        result = response.json()
        access_token = result.get("access_token")
        print(f"✅ 登录成功，Token: {access_token[:50] if access_token else 'None'}...")
        return True
    else:
        print(f"❌ 登录失败: {response.status_code} - {response.text}")
        return False


async def test_create_plan_async():
    """异步创建行程测试"""
    global access_token, trip_id
    
    if not access_token:
        print("❌ 请先登录")
        return False
    
    url = f"{BASE_URL}/api/v1/plan/text"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    start_date = (date.today() + timedelta(days=5)).isoformat()
    end_date = (date.today() + timedelta(days=12)).isoformat()
    
    data = {
        "destination": "东京",
        "start_date": start_date,
        "end_date": end_date,
        "budget_cny": 15000.0,
        "people": "2大1小",
        "preferences": "喜欢美食和动漫"
    }
    
    print(f"\n📝 发送行程请求...")
    response = await test_async_request("POST", url, json=data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        trip_id = result.get("trip_id")
        print(f"✅ 行程创建成功: {trip_id}")
        return True
    else:
        print(f"❌ 创建失败: {response.status_code} - {response.text}")
        return False


async def test_concurrent_requests():
    """测试并发请求"""
    if not access_token:
        await test_login_async()
    
    if not access_token:
        return
    
    url = f"{BASE_URL}/api/v1/auth/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 并发发送5个请求
    tasks = [test_async_request("GET", url, headers=headers) for _ in range(5)]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in responses if isinstance(r, httpx.Response) and r.status_code == 200)
    print(f"\n✅ 并发测试: {success_count}/5 请求成功")


async def main():
    """主异步测试流程"""
    print("\n🚀 异步API测试")
    print("="*60)
    
    # 登录
    await test_login_async()
    
    # 创建行程
    await test_create_plan_async()
    
    # 并发测试
    await test_concurrent_requests()
    
    print("\n✅ 异步测试完成")


if __name__ == "__main__":
    asyncio.run(main())


