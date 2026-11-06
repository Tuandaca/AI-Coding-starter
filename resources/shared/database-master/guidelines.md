# Database Master Guidelines

## Schema Design

### Naming Conventions
- Tables: plural, snake_case (`users`, `order_items`)
- Columns: snake_case (`created_at`, `user_id`)
- Primary keys: `id` (UUID or bigserial)
- Foreign keys: `{table}_id` (`user_id`)
- Indexes: `idx_{table}_{column}`
- Unique constraints: `uq_{table}_{column}`

### Data Types
- Use UUID for primary keys (distributed systems)
- Use `timestamptz` for timestamps
- Use `numeric`/`decimal` for money
- Use `jsonb` for flexible attributes
- Avoid `text` when `varchar(n)` suffices

### Relationships
- One-to-many: FK on "many" side
- Many-to-many: junction table
- One-to-one: shared PK or unique FK

## Migrations

### Principles
- One migration per logical change
- Never modify applied migrations
- Test on production-scale data
- Include rollback procedures

### Naming
- `YYYYMMDDHHMMSS_description.sql`
- Example: `20240115120000_add_user_preferences.sql`

## Performance

### Indexing
- Index foreign keys
- Composite indexes for multi-column queries
- Partial indexes for filtered queries
- Monitor unused indexes

### Query Optimization
- Use EXPLAIN ANALYZE
- Avoid N+1 queries
- Use connection pooling (PgBouncer)
- Read replicas for heavy reads

## Safety

- Soft deletes (`deleted_at`) over hard deletes
- Audit tables for critical data
- Point-in-time recovery configured
- Automated backups verified
