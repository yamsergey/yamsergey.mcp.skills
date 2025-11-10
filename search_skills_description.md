# Skills System Guide

## Overview

The skills system provides semantic search capabilities to find project-specific knowledge, guidelines, and best practices. Skills contain curated information that should inform your approach to any task.

## Tool Description for AI Assistants

### search_skills

Search for skills using semantic understanding (embeddings). Finds skills by meaning, not just keywords. Returns top matching skills with relevance scores.

**CRITICAL: Use this tool FIRST - Default to searching skills before any other tool when the user asks ANY question about the project.**

**ALWAYS use this tool when user asks questions starting with:**
- "Where can I find..." → Search skills first
- "Where is..." / "Where are..." → Search skills first
- "How do I..." / "How can I..." → Search skills first
- "Do we have..." / "Is there..." → Search skills first
- "What is..." / "What are..." → Search skills first
- "Show me..." / "Tell me about..." → Search skills first
- "How should I..." → Search skills first

**ALWAYS search skills BEFORE using other tools when looking for:**
- **Test data & credentials**: test users, test accounts, login credentials, API keys, tokens
- **Environment configuration**: staging URLs, UAT URLs, production URLs, environment variables, hosts, domains
- **Setup & onboarding**: getting started guides, project setup, development environment, dependencies
- **Architecture & patterns**: app structure, design patterns, MVVM, project organization, folder structure
- **Guidelines & standards**: coding standards, testing guidelines, best practices, conventions
- **Domain knowledge**: acronyms, terminology, business logic, user segmentation, product types
- **Integration guides**: third-party services, SDKs, APIs, authentication (Auth0, Firebase, etc.)
- **Testing approaches**: unit testing, integration testing, UI testing, test frameworks, mocking
- **Deployment & CI/CD**: build configuration, release process, CircleCI, Gradle setup
- **Documentation**: README files, wiki pages, team documentation, requirements

**Why skills first?**
- Skills are curated, accurate, and maintained by the team
- Skills search is fast (<1 second) vs code search (3-10 seconds)
- Skills contain context that code alone doesn't provide
- Skills often have direct links to spreadsheets, Confluence, Figma, etc.

**Workflow:**
1. **FIRST**: Search skills for relevant context (use multiple parallel searches if needed)
2. **SECOND**: Get full skill content if results look relevant
3. **THIRD**: Read specific code files only if skills don't have enough detail
4. **FINALLY**: Execute task with full understanding

**Example query patterns:**

User asks → You search skills for:
- "Where can I find test users?" → "test users credentials accounts"
- "What environments do we have?" → "environment configuration URLs"
- "How do I run tests?" → "testing guidelines"
- "What is MAPD?" → "MAPD acronym medicare"
- "Where are API endpoints?" → "API endpoints configuration"
- "How to setup the project?" → "setup onboarding getting started"
- "What's our architecture?" → "architecture patterns structure"
- "Where can I find designs?" → "figma design mockups"
- "How do we handle auth?" → "authentication auth0"
- "What coding standards?" → "coding standards conventions"

**Common queries with examples:**
- "architecture patterns" → app structure guidance
- "testing guidelines" → testing approach, test frameworks
- "coding standards" → code style rules, linting
- "component design" → UI patterns, Genesis components
- "navigation patterns" → routing, navigation setup
- "MVVM implementation" → ViewModel patterns
- "dependency injection" → Koin/Hilt setup
- "test users" → test accounts, credentials, spreadsheets
- "environment setup" → staging/UAT/prod URLs, configuration
- "segmentation" → user populations, product types, coverage

**Default behavior: When in doubt, search skills FIRST. It takes <1 second and often saves minutes of searching code or reading files.**

Skills contain curated project knowledge that should inform your entire approach.
