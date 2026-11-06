# Deploy Workflow

## Purpose
Safely deploy applications to production with proper validation and rollback capability.

## Steps

1. **Pre-Deployment**
   - All tests passing
   - Security scan clean
   - Dependency audit clean
   - Version tagged
   - Changelog updated

2. **Staging Validation**
   - Deploy to staging
   - Smoke tests
   - Performance baseline
   - Stakeholder approval

3. **Production Deploy**
   - Blue-green or canary
   - Health checks passing
   - Metrics stable
   - Feature flags configured

4. **Post-Deployment**
   - Monitoring alerting active
   - Error rate baseline
   - Performance verification
   - Rollback plan ready

5. **Validation Period**
   - 30-60 min heightened monitoring
   - Key metric verification
   - User feedback monitoring
   - Incident response ready

## Rollback Triggers
- Error rate > 1%
- Latency p99 > 2x baseline
- Critical user journey broken
- Data integrity issues

## Outputs
- Successful production deployment
- Monitoring active
- Rollback capability verified
- Deployment record
