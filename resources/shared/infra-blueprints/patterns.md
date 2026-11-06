# Infrastructure Blueprints

## Common Patterns

### Web Application (Standard)
```
┌─────────────────────────────────────┐
│           Load Balancer             │
└──────────────┬──────────────────────┘
               │
    ┌──────────┴──────────┐
    ▼                     ▼
┌───────┐             ┌───────┐
│ App 1 │             │ App 2 │  (Auto-scaling group)
└───────┘             └───────┘
    │                     │
    └──────────┬──────────┘
               ▼
        ┌────────────┐
        │  Database  │  (Primary + Read Replica)
        └────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
    ┌───────┐     ┌───────┐
    │ Cache │     │ Queue │
    └───────┘     └───────┘
```

### Serverless API
```
┌─────────────┐
│  API Gateway │
└──────┬────────┘
       │
  ┌────┴────┐
  ▼         ▼
┌─────┐ ┌─────┐
│Fn: A│ │Fn: B│  (Lambda/Cloud Functions)
└─────┘ └─────┘
  │         │
  └────┬────┘
       ▼
  ┌─────────┐
  │  DynamoDB│
  └─────────┘
```

### Static Site + API
```
┌─────────────┐     ┌─────────────┐
│    CDN      │     │  API Server │
│ (Static)    │────▶│  (Dynamic)  │
└─────────────┘     └─────────────┘
                          │
                   ┌──────┴──────┐
                   ▼             ▼
              ┌────────┐    ┌────────┐
              │Database│    │ External│
              └────────┘    │ APIs   │
                            └────────┘
```

## Environment Strategy

- **Local**: Docker Compose / LocalStack
- **Preview**: Per-PR ephemeral environments
- **Staging**: Production-like, subset of data
- **Production**: Full HA, monitoring, alerts

## IaC Principles

- Terraform for cloud resources
- Modular, reusable modules
- State locking and remote backend
- Plan required before apply
- Drift detection scheduled
