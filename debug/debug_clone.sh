#!/bin/bash
# Git 클론 디버깅 스크립트

POD_NAME="devpod-auto-worke-b056e"
GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"
GITHUB_REPO="justinbuzzni/auto-worker-demo"

echo "1. Git 설정 확인"
kubectl exec -n devpod $POD_NAME -- bash -c "git config --list | grep -E 'user|credential'"

echo -e "\n2. GitHub 연결 테스트"
kubectl exec -n devpod $POD_NAME -- bash -c "git ls-remote https://$GITHUB_TOKEN@github.com/$GITHUB_REPO.git HEAD"

echo -e "\n3. 기존 디렉토리 확인"
kubectl exec -n devpod $POD_NAME -- bash -c "ls -la ~/ | grep auto-worker"

echo -e "\n4. 클론 테스트 (테스트 디렉토리)"
kubectl exec -n devpod $POD_NAME -- bash -c "cd ~ && rm -rf test-clone && git clone https://$GITHUB_TOKEN@github.com/$GITHUB_REPO.git test-clone && echo 'Clone successful!' && ls -la test-clone/"