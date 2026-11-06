# Metrics Guidelines

## Key Metrics Categories

### Business Metrics
- **Conversion Rate**: Visitors → Customers
- **Activation Rate**: Signups → Active users
- **Retention**: D1, D7, D30, M6
- **Churn Rate**: Monthly/Annual
- **LTV**: Lifetime Value
- **CAC**: Customer Acquisition Cost

### Product Metrics
- **DAU/MAU**: Daily/Monthly Active Users
- **Session Duration**: Engagement depth
- **Feature Adoption**: % users using feature
- **Funnel Completion**: Step-by-step conversion
- **Error Rate**: User-facing errors

### Technical Metrics
- **Availability**: Uptime % (99.9%, 99.99%)
- **Latency**: p50, p95, p99 response times
- **Error Rate**: 5xx, 4xx rates
- **Throughput**: Requests/second
- **Saturation**: CPU, memory, disk, network

## SLI/SLO/SLA Framework

### Service Level Indicators (SLIs)
- Latency: % requests < 200ms
- Availability: % uptime
- Quality: % requests without errors
- Durability: % data not lost

### Service Level Objectives (SLOs)
- Latency: 95% of requests < 200ms
- Availability: 99.9% uptime/month
- Error rate: < 0.1% 5xx errors

### Service Level Agreements (SLAs)
- Customer-facing commitments
- Penalties for breach
- Measured over billing period

## Implementation

### Instrumentation
- OpenTelemetry for traces/metrics/logs
- RED metrics (Rate, Errors, Duration)
- USE metrics (Utilization, Saturation, Errors)

### Alerting
- Alert on SLO burn rate
- Multi-window, multi-burn-rate
- Page for critical, ticket for warning
- Runbook links in alerts

### Dashboards
- Golden signals (Latency, Traffic, Errors, Saturation)
- Business KPI overview
- Service-specific details
- On-call handoff context
