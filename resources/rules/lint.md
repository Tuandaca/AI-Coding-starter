# Lint Rules

## General
- No trailing whitespace
- No tabs (use 2 spaces)
- Max line length: 100 characters
- UTF-8 encoding
- Unix line endings (LF)

## JavaScript/TypeScript
- Use const/let, no var
- Prefer arrow functions
- Use optional chaining (?.)
- Use nullish coalescing (??)
- No console.log in production code
- No debugger statements

## Python
- Follow PEP 8
- Use type hints
- Max line length: 88 (Black)
- Use f-strings
- Prefer pathlib over os.path

## Rust
- Follow rustfmt
- Clippy pedantic warnings
- No unwrap() in production (use ? or expect)
- Prefer anyhow/thiserror for errors

## Go
- Follow gofmt
- Use go vet
- Error handling explicit
- No naked returns in functions > 10 lines
