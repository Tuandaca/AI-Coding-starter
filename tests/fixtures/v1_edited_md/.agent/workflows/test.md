# Test Workflow

## Purpose
Execute comprehensive testing strategy following the test pyramid.

## Steps

1. **Unit Tests**
   - Run on every file change
   - Target: >80% coverage
   - Fast execution (< 30s)
   - Isolated, deterministic

2. **Integration Tests**
   - Run on PR creation
   - API contract tests
   - Database integration
   - External service mocks

3. **E2E Tests**
   - Run on merge to main
   - Critical user journeys
   - Real browser (Playwright)
   - Staging environment

4. **Specialized Tests**
   - Visual regression
   - Accessibility (axe-core)
   - Performance benchmarks
   - Security scanning
   - Mutation testing (periodic)

5. **CI/CD Integration**
   - Gate merges on test results
   - Coverage reporting
   - Flaky test detection
   - Test analytics dashboard

## Outputs
- Test execution reports
- Coverage metrics
- Quality gates status
- Regression detection
- Confidence for deployment
