# Debug Workflow

## Purpose
Systematic approach to diagnosing and resolving production issues.

## Steps

1. **Triage**
   - Assess severity and impact
   - Check known issues/runbooks
   - Identify affected users/systems
   - Communicate status

2. **Investigation**
   - Check dashboards/alerts
   - Review recent deployments
   - Analyze logs/traces
   - Correlate with metrics
   - Form hypothesis

3. **Diagnosis**
   - Test hypothesis
   - Isolate root cause
   - Determine fix strategy
   - Assess blast radius

4. **Resolution**
   - Implement fix (hotfix/config/rollback)
   - Verify in staging if possible
   - Deploy with monitoring
   - Confirm resolution

5. **Post-Mortem**
   - Timeline reconstruction
   - Root cause analysis
   - Action items
   - Documentation update
   - Knowledge sharing

## Debugging Tools
- Distributed tracing (Jaeger, Zipkin)
- Log aggregation (Loki, ELK)
- Metrics (Prometheus, Grafana)
- Profiling (py-spy, pprof)
- Database query analysis

## Outputs
- Issue resolved
- Root cause documented
- Prevention measures
- Runbook updated
- Team knowledge increased
