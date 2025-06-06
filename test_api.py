#!/usr/bin/env python
import requests
import json
import time

# API 서버 URL
API_BASE_URL = "http://localhost:15001"  # 원래 API 서버

# 테스트 데이터
test_data = {
    "devpod_name": "auto-worker-demo",
    "github_repo": "justinbuzzni/auto-worker-demo",
    "github_token": "YOUR_GITHUB_TOKEN_HERE",
    "task_description": "streamlit으로 문자열을 입력 받으면 그 결과를 화면에 노란 색으로 2번 new line 으로 출력해줘"
}

def test_create_task():
    """작업 생성 테스트"""
    print("1. 작업 생성 중...")
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/create-task", json=test_data)
        response.raise_for_status()
        
        result = response.json()
        task_id = result.get('task_id')
        print(f"✅ 작업 생성 성공! Task ID: {task_id}")
        return task_id
    except Exception as e:
        print(f"❌ 작업 생성 실패: {e}")
        return None

def check_task_status(task_id):
    """작업 상태 확인"""
    print(f"\n2. 작업 상태 확인 중... (Task ID: {task_id})")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/task-status/{task_id}")
        response.raise_for_status()
        
        task_data = response.json()
        status = task_data.get('status', 'unknown')
        progress = task_data.get('progress', 0)
        claude_status = task_data.get('claude_status', '')
        
        print(f"상태: {status}")
        print(f"진행률: {progress}%")
        if claude_status:
            print(f"Claude 상태: {claude_status}")
        
        # 최근 로그 5개 출력
        logs = task_data.get('logs', [])
        if logs:
            print("\n최근 로그:")
            for log in logs[-5:]:
                print(f"  - {log}")
        
        return status, task_data
    except Exception as e:
        print(f"❌ 상태 확인 실패: {e}")
        return None, None

def monitor_task(task_id, max_wait=300):
    """작업 모니터링 (최대 5분)"""
    print(f"\n3. 작업 모니터링 시작 (최대 {max_wait}초 대기)")
    
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < max_wait:
        status, task_data = check_task_status(task_id)
        
        if status != last_status:
            print(f"\n[{int(time.time() - start_time)}초] 상태 변경: {last_status} → {status}")
            last_status = status
        
        if status in ['completed', 'failed', 'interrupted']:
            print(f"\n✅ 작업 완료! 최종 상태: {status}")
            
            # 서버 URL 확인
            if task_data and task_data.get('app_url'):
                print(f"🌐 앱 URL: {task_data['app_url']}")
            
            return status
        
        time.sleep(5)  # 5초마다 확인
    
    print(f"\n⏱️ 시간 초과 ({max_wait}초)")
    return status

def test_dashboard():
    """대시보드 API 테스트"""
    print("\n4. 대시보드 API 테스트")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/dashboard")
        response.raise_for_status()
        
        data = response.json()
        print(f"총 작업 수: {data.get('total_tasks', 0)}")
        print(f"실행 중: {data.get('running_tasks', 0)}")
        print(f"완료: {data.get('completed_tasks', 0)}")
        print(f"실패: {data.get('failed_tasks', 0)}")
        
        return True
    except Exception as e:
        print(f"❌ 대시보드 API 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("=== Remote Developer API 테스트 시작 ===\n")
    
    # 대시보드 테스트
    if not test_dashboard():
        print("API 서버가 응답하지 않습니다. 서버가 실행 중인지 확인하세요.")
        return
    
    # 작업 생성
    task_id = test_create_task()
    if not task_id:
        return
    
    # 작업 모니터링
    monitor_task(task_id)
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()