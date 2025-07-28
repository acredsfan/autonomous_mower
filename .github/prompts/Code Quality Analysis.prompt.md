---
mode: agent
tools: ['codebase', 'editFiles', 'fetch', 'sequential-thinking', 'server-memory']
description: Conduct a comprehensive code quality analysis of the codebase, ensuring adherence to best practices, architectural integrity, and optimal performance.
---

Analyze the entire codebase to ensure code quality, architectural consistency, and error-free implementation across all components and modules.

## Analysis Scope

Review all source files, templates, and static resources with focus on:
- Main application files and entry points
- All templates (inline and external)
- Client-side code (JavaScript, TypeScript, etc.)
- Static resources and assets
- Configuration files and data sources
- Build and deployment scripts

## Critical Requirements

### 1. Architectural Compliance
- **Verify separation of concerns**: Ensure modules and components maintain proper boundaries
- **Design pattern adherence**: Check implementation matches documented architectural patterns
- **Dependency management**: Verify proper dependency injection and coupling levels
- **Data flow integrity**: Ensure data flows follow documented pathways without unauthorized crossover

### 2. Code Quality Checks
- **Framework best practices**: Proper use of framework-specific patterns and conventions
- **Error handling**: Comprehensive try-catch blocks, error boundaries, and graceful degradation
- **Resource management**: Verify proper cleanup of resources (files, connections, memory)
- **Code organization**: Check for proper file structure, naming conventions, and modularity

### 3. Performance & Efficiency
- **API optimization**: Rate limiting compliance and efficient request handling
- **I/O efficiency**: Proper handling of file operations and data processing
- **Caching strategies**: Verify caching implementations and cache invalidation
- **Asset optimization**: Efficient loading of static resources and lazy loading where appropriate

### 4. Security & Best Practices
- **Secrets management**: Ensure sensitive data is properly protected (API keys, credentials)
- **Input validation**: Check all user inputs are validated and sanitized
- **Injection prevention**: Verify protection against SQL, XSS, and other injection attacks
- **Access control**: Validate authentication and authorization implementations

### 5. Feature Completeness
- **Core functionality**: Confirm all documented features work as specified
- **Edge case handling**: Verify graceful handling of boundary conditions
- **Integration points**: Check external service integrations work correctly
- **Cross-platform compatibility**: Ensure consistent behavior across supported platforms

## Success Criteria

1. **Clean architecture**: No violations of established architectural patterns
2. **Error resilience**: All critical paths handle failures gracefully
3. **Consistent behavior**: Same inputs produce predictable outputs
4. **Performance standards**: Operations complete within acceptable time limits
5. **Code maintainability**: Clear separation of concerns, proper documentation, DRY principles

## Output Format

Provide:
1. **Executive Summary**: Overall health score and critical issues count
2. **Architecture Violations**: Any deviations from established design patterns
3. **Code Issues**: Categorized by severity (Critical/High/Medium/Low)
4. **Performance Bottlenecks**: Identified inefficiencies with suggested fixes
5. **Security Vulnerabilities**: Any potential security risks discovered
6. **Recommendations**: Prioritized list of improvements with code examples
7. **Compliance Checklist**: Pass/Fail for each requirement category
8. **Task List**: Actionable tasks for developers to address issues found

## Additional Considerations

- **Technical Debt**: Identify areas accumulating technical debt
- **Test Coverage**: Assess unit, integration, and e2e test coverage
- **Documentation**: Evaluate code comments and API documentation
- **Scalability**: Consider potential scaling issues and bottlenecks
- **Monitoring**: Check for proper logging and observability

Focus on actionable insights that improve code quality, maintainability, and reliability while respecting the project's specific architectural decisions and constraints.