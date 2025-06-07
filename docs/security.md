# Security Guide

This document outlines the security practices and considerations for Remote Developer.

## GitHub Token Security

### Client-Side Storage Only

Remote Developer implements a security-first approach for GitHub token management:

- **No Server Storage**: GitHub tokens are NEVER stored in the MongoDB database or server-side storage
- **Browser localStorage**: Tokens are stored only in the user's browser localStorage
- **Per-Session**: Each user session manages their own token independently
- **No Persistence**: Tokens are not persisted across different browsers or devices

### Token Usage Flow

1. **User Input**: User enters GitHub token in the web interface
2. **localStorage Storage**: Token is stored in browser's localStorage
3. **API Requests**: Token is sent with each API request that requires GitHub access
4. **Memory Only**: Server processes the token in memory and discards it immediately
5. **No Logging**: GitHub tokens are never logged or saved to files

### Implementation Details

#### Frontend (Browser)
```javascript
// Store token in localStorage
localStorage.setItem('github_token', userToken);

// Retrieve token for API calls
const token = localStorage.getItem('github_token');

// Send token with requests
axios.post('/api/task/create-pr', {
    pr_title: title,
    pr_body: body,
    github_token: token  // Sent but not stored on server
});
```

#### Backend (Server)
```python
# Token received in request
github_token = data.get('github_token')

# Used immediately for Git operations
auth_cmd = f'echo {github_token} | gh auth login --with-token'

# Token is NOT saved to database
task_data = {
    'task_id': task_id,
    'devpod_name': devpod_name,
    'github_repo': github_repo,
    # GitHub token intentionally excluded for security
}
```

### Best Practices

#### For Users

1. **Use Personal Access Tokens**: Create fine-grained personal access tokens instead of using passwords
2. **Minimal Permissions**: Grant only necessary permissions (repository access, PR creation)
3. **Regular Rotation**: Rotate tokens regularly (every 3-6 months)
4. **Secure Environment**: Only use on trusted devices and networks
5. **Clear Browser Data**: Clear localStorage when using shared computers

#### For Administrators

1. **No Token Logging**: Ensure application logs don't capture GitHub tokens
2. **HTTPS Only**: Always use HTTPS to encrypt token transmission
3. **Environment Variables**: Use environment variables for any service tokens
4. **Access Auditing**: Monitor GitHub organization access logs

### Token Permissions Required

Remote Developer requires the following GitHub token permissions:

#### Repository Access
- `repo` - Full control of private repositories (for cloning, pushing)
- `public_repo` - Access to public repositories

#### Pull Request Management
- `repo:status` - Access commit status
- `repo_deployment` - Access deployment status
- `public_repo` - Create pull requests on public repos

#### Optional Permissions
- `read:org` - Read organization membership (if working with org repositories)
- `user:email` - Access user email (for git commits)

### Security Considerations

#### Threats Mitigated

1. **Database Breaches**: Tokens not in database, so unaffected by DB compromises
2. **Server Memory Dumps**: Tokens only in memory briefly during request processing
3. **Log Analysis**: Tokens excluded from all application logs
4. **Unauthorized Access**: Each user manages their own token independently

#### Remaining Risks

1. **Browser Storage**: localStorage is accessible to XSS attacks
2. **Network Interception**: Tokens transmitted over network (mitigated by HTTPS)
3. **Malicious Extensions**: Browser extensions could potentially access localStorage
4. **Physical Access**: Someone with device access could view localStorage

#### Mitigation Strategies

1. **HTTPS Enforcement**: All communication encrypted in transit
2. **Content Security Policy**: Implement CSP headers to prevent XSS
3. **Token Validation**: Validate tokens before use
4. **Session Management**: Clear tokens on logout or session expiry

## Environment Variables Security

### Sensitive Configuration

Keep sensitive configuration in environment variables, not in code:

```bash
# MongoDB credentials
MONGODB_USER=your_mongodb_user
MONGODB_PASSWORD=your_mongodb_password

# API keys (if any)
CLAUDE_CODE_API_KEY=your_api_key

# GitHub integration (for server operations)
GITHUB_TOKEN=server_token_if_needed
```

### Environment File Protection

```bash
# Secure .env file permissions
chmod 600 .env

# Never commit .env files
echo ".env" >> .gitignore
```

## Network Security

### CORS Configuration

```python
# Restrict CORS to specific domains in production
CORS(app, origins=[
    "https://your-domain.com",
    "https://api.your-domain.com"
])
```

### Rate Limiting

Consider implementing rate limiting for API endpoints:

```python
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route('/api/create-task', methods=['POST'])
@limiter.limit("10 per minute")
def create_task():
    # Implementation
```

## DevPod Security

### Container Isolation

- DevPod containers provide process and filesystem isolation
- Each task runs in a separate container environment
- No shared state between different tasks

### Resource Limits

Configure resource limits in DevPod:

```yaml
# devpod.yaml
resources:
  limits:
    cpu: "2"
    memory: "4Gi"
  requests:
    cpu: "0.5"
    memory: "1Gi"
```

## Monitoring and Auditing

### Security Logging

Log security-relevant events without sensitive data:

```python
# Good: Log action without token
logger.info(f"GitHub authentication attempt for repo {github_repo}")

# Bad: Don't log tokens
# logger.info(f"Using token {github_token}")
```

### Access Monitoring

- Monitor failed authentication attempts
- Track unusual API usage patterns
- Alert on suspicious repository access

## Incident Response

### Token Compromise

If a GitHub token is compromised:

1. **Revoke Immediately**: Revoke the token in GitHub settings
2. **Generate New Token**: Create a new token with minimal required permissions
3. **Update Browser**: Clear localStorage and enter new token
4. **Audit Activity**: Review GitHub audit logs for unauthorized activity

### Security Updates

- Keep Remote Developer updated to latest version
- Monitor security advisories for dependencies
- Regularly update DevPod and container images

## Compliance Considerations

### Data Protection

- User GitHub tokens are not stored permanently
- Task logs may contain sensitive information - implement retention policies
- Consider GDPR implications for EU users

### Access Controls

- Implement user authentication if needed
- Use GitHub organization permissions to control repository access
- Consider implementing role-based access control

---

**Note**: This security model prioritizes simplicity and transparency. For enterprise deployments, consider additional security measures such as:

- OAuth-based GitHub integration
- Centralized secret management
- Enhanced audit logging
- Multi-factor authentication
- Network security groups
- Container security scanning