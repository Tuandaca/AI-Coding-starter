# Security Workflow

## Purpose
Maintain security posture throughout the development lifecycle.

## Steps

1. **Development Phase**
   - Secure coding practices
   - Dependency scanning (SAST)
   - Secret scanning
   - Code review with security lens
   - Threat modeling for new features

2. **Pre-Deployment**
   - Container/image scanning
   - Infrastructure scanning (IaC)
   - Penetration testing (critical changes)
   - Compliance validation
   - Security gate in CI/CD

3. **Runtime Protection**
   - WAF rules
   - Runtime application self-protection
   - Anomaly detection
   - Audit logging
   - Incident response readiness

4. **Ongoing**
   - Dependency updates (automated)
   - Vulnerability monitoring
   - Regular penetration tests
   - Security training
   - Incident drills

## Outputs
- Secure codebase
- Vulnerability-free dependencies
- Compliant infrastructure
- Monitoring active
- Incident response ready
