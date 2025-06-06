#!/bin/bash
# Remote Developer 수동 디버깅 스크립트

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 작업 정보
DEVPOD_NAME="auto-worker-demo"
GITHUB_REPO="justinbuzzni/auto-worker-demo"
GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"
TASK_DESCRIPTION="streamlit으로 문자열을 입력 받으면 그 결과를 화면에 파란색으로 4번 new line 으로 출력해줘"
REPO_NAME=$(echo $GITHUB_REPO | cut -d'/' -f2)

echo -e "${BLUE}=== Remote Developer 수동 디버깅 시작 ===${NC}"
echo "DevPod: $DEVPOD_NAME"
echo "Repository: $GITHUB_REPO"
echo "Task: $TASK_DESCRIPTION"
echo ""

# 1. DevPod 상태 확인
echo -e "${YELLOW}1. DevPod 상태 확인${NC}"
/Users/namsangboy/.local/bin/devpod list | grep $DEVPOD_NAME
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ DevPod를 찾을 수 없습니다${NC}"
    exit 1
fi

# 2. DevPod 시작
echo -e "\n${YELLOW}2. DevPod 시작${NC}"
/Users/namsangboy/.local/bin/devpod up $DEVPOD_NAME
echo -e "${GREEN}✅ DevPod 준비 완료${NC}"

# 3. Pod 이름 찾기
echo -e "\n${YELLOW}3. Kubernetes Pod 찾기${NC}"
POD_NAME=$(kubectl get pods -n devpod | grep "devpod-${DEVPOD_NAME:0:10}" | awk '{print $1}' | head -1)
if [ -z "$POD_NAME" ]; then
    echo -e "${RED}❌ Pod를 찾을 수 없습니다${NC}"
    kubectl get pods -n devpod
    exit 1
fi
echo -e "${GREEN}✅ Pod 찾음: $POD_NAME${NC}"

# 4. Git 설정
echo -e "\n${YELLOW}4. Git 설정${NC}"
kubectl exec -n devpod $POD_NAME -- bash -c "git config --global user.name 'Auto Worker'"
kubectl exec -n devpod $POD_NAME -- bash -c "git config --global user.email 'auto-worker@example.com'"
kubectl exec -n devpod $POD_NAME -- bash -c "git config --global credential.helper store"
kubectl exec -n devpod $POD_NAME -- bash -c "echo 'https://$GITHUB_TOKEN@github.com' > ~/.git-credentials"
echo -e "${GREEN}✅ Git 설정 완료${NC}"

# 5. 레포지토리 클론/업데이트
echo -e "\n${YELLOW}5. 레포지토리 클론/업데이트${NC}"
REPO_EXISTS=$(kubectl exec -n devpod $POD_NAME -- bash -c "cd ~/$REPO_NAME && pwd" 2>/dev/null)
if [ -n "$REPO_EXISTS" ]; then
    echo "레포지토리가 이미 존재합니다. 업데이트 중..."
    kubectl exec -n devpod $POD_NAME -- bash -c "cd ~/$REPO_NAME && git fetch origin && git reset --hard origin/main"
else
    echo "레포지토리 클론 중..."
    kubectl exec -n devpod $POD_NAME -- bash -c "cd ~ && git clone https://$GITHUB_TOKEN@github.com/$GITHUB_REPO.git"
fi
echo -e "${GREEN}✅ 레포지토리 준비 완료${NC}"

# 6. Node.js 확인 및 설치
echo -e "\n${YELLOW}6. Node.js 확인${NC}"
NODE_CHECK=$(kubectl exec -n devpod $POD_NAME -- bash -c "which node")
if [ -z "$NODE_CHECK" ]; then
    echo "Node.js 설치 중..."
    kubectl exec -n devpod $POD_NAME -- bash -c "apt-get update && apt-get install -y nodejs npm"
fi
echo -e "${GREEN}✅ Node.js 준비 완료${NC}"

# 7. Claude 설치
echo -e "\n${YELLOW}7. Claude Code 설치${NC}"
kubectl exec -n devpod $POD_NAME -- bash -c "npm install -g @anthropic-ai/claude-code || true"

# Claude 설정 파일 생성
echo "Claude 설정 파일 생성 중..."
kubectl exec -n devpod $POD_NAME -- bash -c 'mkdir -p ~/.claude && cat > ~/.claude/settings.json << EOF
{
  "permissions": {
    "allow": [
      "Write(*)",
      "Read(*)",
      "Edit(*)",
      "Bash(*)",
      "Grep(*)",
      "Glob(*)",
      "MultiEdit(*)"
    ],
    "deny": []
  },
  "enableAllProjectMcpServers": false
}
EOF'

CLAUDE_CHECK=$(kubectl exec -n devpod $POD_NAME -- bash -c "which claude")
if [ -n "$CLAUDE_CHECK" ]; then
    echo -e "${GREEN}✅ Claude 설치 완료: $CLAUDE_CHECK${NC}"
else
    echo -e "${YELLOW}⚠️  Claude를 찾을 수 없습니다${NC}"
fi

# 8. 브랜치 생성
echo -e "\n${YELLOW}8. 새 브랜치 생성${NC}"
BRANCH_NAME="auto-pr-$(date +%s)"
kubectl exec -n devpod $POD_NAME -- bash -c "cd ~/$REPO_NAME && git checkout -b $BRANCH_NAME"
echo -e "${GREEN}✅ 브랜치 생성: $BRANCH_NAME${NC}"

# 9. Claude 실행
echo -e "\n${YELLOW}9. Claude 실행${NC}"
echo "Task: $TASK_DESCRIPTION"
echo ""
echo "Claude 실행 중... (최대 5분 대기)"

# Claude 실행 스크립트 생성
kubectl exec -n devpod $POD_NAME -- bash -c "cd ~/$REPO_NAME && cat > run_claude_manual.sh << 'EOF'
#!/bin/bash
echo '=== Claude 실행 시작 ==='
echo 'Task: $TASK_DESCRIPTION'

if command -v claude &> /dev/null; then
    echo 'Claude 명령어 위치:' \$(which claude)
    
    # Claude 실행 (타임아웃 5분)
    timeout 300 claude --print \"$TASK_DESCRIPTION\" 2>&1 | tee claude_manual_output.txt
    
    echo ''
    echo '=== Claude 실행 완료 ==='
else
    echo 'Claude를 찾을 수 없습니다!'
    exit 1
fi

# 생성된 파일 확인
echo ''
echo '=== 생성된 파일 ==='
ls -la *.py 2>/dev/null || echo 'Python 파일 없음'
EOF"

# 스크립트 실행
kubectl exec -n devpod $POD_NAME -- bash -c "cd ~/$REPO_NAME && chmod +x run_claude_manual.sh && bash run_claude_manual.sh"

# 10. 결과 확인
echo -e "\n${YELLOW}10. 결과 확인${NC}"
echo "생성된 파일들:"
kubectl exec -n devpod $POD_NAME -- bash -c "cd ~/$REPO_NAME && ls -la"

echo -e "\napp.py 내용 (첫 20줄):"
kubectl exec -n devpod $POD_NAME -- bash -c "cd ~/$REPO_NAME && [ -f app.py ] && head -20 app.py || echo 'app.py 파일이 없습니다'"

# 11. Git 커밋
echo -e "\n${YELLOW}11. 변경사항 커밋${NC}"
kubectl exec -n devpod $POD_NAME -- bash -c "cd ~/$REPO_NAME && git add -A && git commit -m 'Task: $TASK_DESCRIPTION' || echo '커밋할 변경사항이 없습니다'"

# 12. Streamlit 실행
echo -e "\n${YELLOW}12. Streamlit 서버 실행${NC}"

# requirements.txt 설치
if kubectl exec -n devpod $POD_NAME -- bash -c "cd ~/$REPO_NAME && [ -f requirements.txt ]"; then
    echo "Python 패키지 설치 중..."
    kubectl exec -n devpod $POD_NAME -- bash -c "cd ~/$REPO_NAME && pip3 install --break-system-packages -r requirements.txt || pip3 install -r requirements.txt"
fi

# 기존 Streamlit 프로세스 종료
kubectl exec -n devpod $POD_NAME -- bash -c "pkill -f streamlit || true"

# Streamlit 실행
if kubectl exec -n devpod $POD_NAME -- bash -c "cd ~/$REPO_NAME && [ -f app.py ]"; then
    echo "Streamlit 앱 시작 중..."
    kubectl exec -n devpod $POD_NAME -- bash -c "cd ~/$REPO_NAME && nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &"
    sleep 3
    
    # 포트 포워딩
    echo -e "\n${YELLOW}13. 포트 포워딩 설정${NC}"
    pkill -f "kubectl port-forward.*8501" || true
    kubectl port-forward -n devpod $POD_NAME 8501:8501 &
    PORT_FORWARD_PID=$!
    
    sleep 2
    echo -e "${GREEN}✅ Streamlit 앱이 실행 중입니다!${NC}"
    echo -e "${BLUE}🌐 브라우저에서 http://localhost:8501 접속${NC}"
    echo ""
    echo "포트 포워딩 PID: $PORT_FORWARD_PID"
    echo "중지하려면: kill $PORT_FORWARD_PID"
else
    echo -e "${RED}❌ app.py 파일을 찾을 수 없습니다${NC}"
fi

echo -e "\n${GREEN}=== 디버깅 완료 ===${NC}"
echo ""
echo "추가 디버깅 명령어:"
echo "  - DevPod 접속: devpod ssh $DEVPOD_NAME"
echo "  - Pod 로그: kubectl logs -n devpod $POD_NAME"
echo "  - Streamlit 로그: kubectl exec -n devpod $POD_NAME -- cat ~/$REPO_NAME/streamlit.log"
echo "  - Claude 출력: kubectl exec -n devpod $POD_NAME -- cat ~/$REPO_NAME/claude_manual_output.txt"