#!/usr/bin/env python
"""실제 작업 테스트 - Claude 실행 및 Streamlit 서버 확인"""
import requests
import json
import time
import subprocess

# API 서버 URL
API_BASE_URL = "http://localhost:15001"

# 테스트 데이터
test_data = {
    "devpod_name": "auto-worker-demo",
    "github_repo": "justinbuzzni/auto-worker-demo",
    "github_token": "YOUR_GITHUB_TOKEN_HERE",
    "task_description": "streamlit으로 문자열을 입력 받으면 그 결과를 화면에 파란색으로 4번 new line 으로 출력해줘"
}

def check_api_server():
    """API 서버 상태 확인"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/dashboard", timeout=5)
        return response.status_code == 200
    except:
        return False

def create_task():
    """작업 생성"""
    print("1. 작업 생성 중...")
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/create-task", json=test_data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        task_id = result.get('task_id')
        print(f"✅ 작업 생성 성공! Task ID: {task_id}")
        return task_id
    except Exception as e:
        print(f"❌ 작업 생성 실패: {e}")
        return None

def get_task_logs(task_id):
    """작업 로그 가져오기 (전체)"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/task-status/{task_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('logs', [])
    except:
        pass
    return []

def monitor_task_detailed(task_id, max_wait=600):
    """작업 상세 모니터링 (최대 10분)"""
    print(f"\n2. 작업 모니터링 시작 (최대 {max_wait}초 대기)")
    
    start_time = time.time()
    last_log_count = 0
    last_status = None
    last_claude_status = None
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{API_BASE_URL}/api/task-status/{task_id}", timeout=5)
            if response.status_code != 200:
                print(f"❌ 상태 확인 실패: HTTP {response.status_code}")
                time.sleep(5)
                continue
                
            task_data = response.json()
            status = task_data.get('status', 'unknown')
            progress = task_data.get('progress', 0)
            claude_status = task_data.get('claude_status', '')
            app_url = task_data.get('app_url', '')
            
            # 상태 변경 시 출력
            if status != last_status:
                print(f"\n[{int(time.time() - start_time)}초] 상태 변경: {last_status} → {status}")
                last_status = status
            
            # Claude 상태 변경 시 출력
            if claude_status != last_claude_status:
                print(f"[{int(time.time() - start_time)}초] Claude 상태: {claude_status}")
                last_claude_status = claude_status
            
            # 새로운 로그만 출력
            logs = task_data.get('logs', [])
            if len(logs) > last_log_count:
                new_logs = logs[last_log_count:]
                for log in new_logs:
                    # 중요한 로그만 출력
                    if any(keyword in log for keyword in ['Error:', '✅', '❌', '🌐', 'CLAUDE_STATUS:', 'Starting Streamlit']):
                        print(f"  📝 {log}")
                last_log_count = len(logs)
            
            # 완료 상태 확인
            if status in ['completed', 'failed', 'interrupted']:
                print(f"\n✅ 작업 종료! 최종 상태: {status}")
                
                if app_url:
                    print(f"🌐 앱 URL: {app_url}")
                    
                    # 포트 포워딩 확인
                    print("\n3. 포트 포워딩 상태 확인...")
                    ps_result = subprocess.run("ps aux | grep 'kubectl port-forward' | grep -v grep", 
                                             shell=True, capture_output=True, text=True)
                    if ps_result.stdout:
                        print("✅ 포트 포워딩 활성화됨:")
                        print(ps_result.stdout.strip())
                    else:
                        print("❌ 포트 포워딩이 활성화되지 않음")
                    
                    # Streamlit 접속 테스트
                    print("\n4. Streamlit 앱 접속 테스트...")
                    try:
                        app_response = requests.get(app_url, timeout=5)
                        if app_response.status_code == 200:
                            print("✅ Streamlit 앱이 정상적으로 실행 중입니다!")
                            print(f"   브라우저에서 {app_url} 접속 가능")
                        else:
                            print(f"⚠️  Streamlit 앱 응답 코드: {app_response.status_code}")
                    except Exception as e:
                        print(f"❌ Streamlit 앱 접속 실패: {e}")
                
                # 실패 시 마지막 로그 출력
                if status == 'failed':
                    print("\n마지막 로그 10개:")
                    for log in logs[-10:]:
                        print(f"  - {log}")
                
                return status
            
            # 진행률 표시 (10% 단위로만)
            if progress % 10 == 0 and progress > 0:
                print(f".", end="", flush=True)
            
        except requests.exceptions.RequestException as e:
            print(f"\n❌ API 요청 실패: {e}")
        
        time.sleep(3)  # 3초마다 확인
    
    print(f"\n⏱️ 시간 초과 ({max_wait}초)")
    return 'timeout'

def main():
    """메인 테스트 함수"""
    print("=== Remote Developer 실제 작업 테스트 ===")
    print(f"작업: {test_data['task_description']}\n")
    
    # API 서버 확인
    if not check_api_server():
        print("❌ API 서버가 응답하지 않습니다. 서버가 실행 중인지 확인하세요.")
        print("   cd /Users/namsangboy/workspace/remote-developer && python -m src.api_server")
        return
    
    print("✅ API 서버가 정상적으로 실행 중입니다.")
    
    # 작업 생성
    task_id = create_task()
    if not task_id:
        return
    
    # 작업 모니터링
    final_status = monitor_task_detailed(task_id)
    
    # 결과 요약
    print("\n=== 테스트 결과 요약 ===")
    print(f"작업 ID: {task_id}")
    print(f"최종 상태: {final_status}")
    
    if final_status == 'completed':
        print("\n다음 단계:")
        print("1. 브라우저에서 http://localhost:8501 접속")
        print("2. 문자열 입력 후 파란색으로 4번 줄바꿈되어 출력되는지 확인")
        
        # 전체 로그 저장
        logs = get_task_logs(task_id)
        if logs:
            with open(f"task_{task_id}_logs.txt", "w") as f:
                f.write("\n".join(logs))
            print(f"\n전체 로그가 task_{task_id}_logs.txt에 저장되었습니다.")

if __name__ == "__main__":
    main()