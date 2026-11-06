# Testing Master Guidelines

## Test Pyramid

```
        /\
       /  \     E2E Tests (few)
      /____\    - Critical user journeys
     /      \   - Real browser/environment
    /________\  Integration Tests (some)
   /          \ - API contracts
  /____________\ - Database integration
 /              \ Unit Tests (many)
/________________\ - Pure functions
                 - Components in isolation
                 - Fast, deterministic
```

## Unit Testing

### Principles
- Test behavior, not implementation
- One assertion per test (ideal)
- AAA pattern: Arrange, Act, Assert
- Fast (< 10ms per test)
- Deterministic, no external deps

### Coverage Targets
- Statements: > 80%
- Branches: > 70%
- Functions: > 80%
- Lines: > 80%

### Test Doubles
- **Mock**: Verify interactions
- **Stub**: Provide canned responses
- **Fake**: Working implementation (in-memory DB)
- **Spy**: Record calls for verification

## Integration Testing

- Test API contracts
- Database operations with testcontainers
- Message queue interactions
- External service mocks (MSW, WireMock)

## E2E Testing

- Critical paths only (login, checkout, core flows)
- Real browser (Playwright, Cypress)
- CI/CD integration
- Flaky test quarantine
- Visual regression testing

## TDD Workflow

1. Write failing test (Red)
2. Minimal code to pass (Green)
3. Refactor with safety (Refactor)
4. Repeat

## CI/CD Integration

- Unit tests on every commit
- Integration tests on PR
- E2E tests on merge/staging
- Coverage reporting
- Mutation testing (optional)
