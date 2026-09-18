# Architectural Decision Record (ADR) - Test Coverage Strategy

**Title:** Test Coverage Organization and Verification Goals
**Status:** [`.pill` Status: Accepted]
**Date:** 2026-09-18
**Authors:** AI Assistant

---

## 📋 Problem Statement / Motivation

The `local-llm-benchmark` project requires a formalized test coverage strategy to ensure comprehensive testing across all layers of the codebase. Current test coverage has gaps, particularly in edge cases and integration scenarios. Without documented goals and organization, it's difficult to measure progress, identify coverage gaps, and ensure all critical code paths are tested.

### Key Concerns

1. **Coverage Goals Unclear** - No formal targets for unit, integration, E2E, and UI test coverage
2. **Test Organization Fragmented** - Tests scattered across multiple directories without clear ownership
3. **Verification Metrics Missing** - No standardized way to report and track coverage improvements
4. **Layer-Specific Testing** - Different layers require different testing approaches and tools

---

## ✨ Decision

The project will adopt a **four-layer testing pyramid** with the following structure:

### 1. Test Organization Structure

```
tests/
├── unit/           # Unit tests with mocked dependencies
│   ├── test_engines/
│   ├── test_benchmarks/
│   ├── test_tasks/
│   ├── test_results/
│   └── test_utils/
├── integration/     # Integration tests with real services
│   ├── test_api/
│   ├── test_db/
│   ├── test_runner/
│   └── test_services/
├── e2e/             # End-to-end tests with browser automation
│   ├── integration/
│   └── tests/
└── utils/
    └── fixtures.py  # Shared test fixtures and utilities
```

### 2. Coverage Goals

| Layer | Target Coverage | Tools | Priority |
|-------|----------------|-------|----------|
| **Unit Tests** | 80%+ | pytest, coverage | Critical |
| **Integration Tests** | 70%+ | pytest, httpx | High |
| **E2E Tests** | 60%+ | playwright, pytest-playwright | Medium |
| **UI Tests** | 70%+ | vitest, playwright | High |

### 3. Testing Pyramid Distribution

```
                    ┌─────────────────┐
                    │     10 E2E      │
                    │       Tests      │
                    └─────────────────┘
                     │         │
                     │         │
                     ▼         ▼
        ┌───────────────────┐┌───────────────────┐
        │     50 Integration││    UI Tests      │
        │       Tests       ││    (70%+ cov)    │
        └───────────────────┘└───────────────────┘
                     │         │
                     │         │
                     ▼         ▼
        ┌───────────────────┐┌───────────────────┐
        │   100 Unit Tests  ││  200 Mock Tests   │
        │       Tests       ││  (Edge cases)    │
        └───────────────────┘└───────────────────┘
```

### 4. Verification Metrics

**Current Test Distribution:**
- Unit tests: 227 tests
- Integration tests: 36 tests
- E2E tests: 35 tests

**Coverage Tools:**
- pytest with pytest-asyncio
- pytest-cov for coverage measurement
- httpx for async client mocking
- playwright for E2E testing
- vitest for UI testing

---

## 💡 Decision Rationale

### Primary Factor: Pyramid of Confidence

The testing pyramid ensures:
- **Foundation (Mock Tests)**: Fast, isolated tests that verify core logic
- **Core (Unit Tests)**: Comprehensive coverage of business logic with mocked dependencies
- **Expansion (Integration Tests)**: Real service interactions with controlled external dependencies
- **Top (E2E Tests)**: End-to-end verification of user workflows

### Secondary Factor: Layer-Specific Tooling

| Layer | Tool | Rationale |
|-------|------|-----------|
| Unit | pytest | Fast, mature, excellent mocking support |
| Integration | pytest + httpx | Async-aware, supports real HTTP clients |
| E2E | playwright | Modern browser automation, cross-browser support |
| UI | vitest | Fast, works with React/Vue/Svelte, component testing |

### Trade-offs Accepted

- **Increased test suite size**: More tests = more maintenance overhead
- **Slower feedback loop for E2E**: Browser tests take longer to run
- **Complexity in test organization**: Multiple directories require discipline

---

## ⚖️ Considerations / Alternatives Considered

### Alternative A: Single Coverage Goal (80%+ Overall)
*Pros:* Simple metric, easy to track
*Cons:* Obscures which layers are weak, doesn't account for test reliability differences
*Rationale for Rejection:* Different layers serve different purposes and require different rigor.

### Alternative B: Minimal E2E Testing
*Pros:* Faster CI, less maintenance
*Cons:* Misses real user scenarios, doesn't catch integration bugs
*Rationale for Rejection:* E2E tests are critical for catching regression bugs that unit tests cannot.

### Alternative C: Property-Based Testing
*Pros:* Exhaustive test generation, finds edge cases
*Cons:* Doesn't cover specific scenarios, requires property definitions
*Rationale for Rejection:* Complements but doesn't replace traditional testing; keep current approach.

### Alternative D: Test-Driven Development (TDD) Mandate
*Pros:* Better code quality, prevents refactoring bugs
*Cons:* Slower initial development, cultural overhead
*Rationale for Rejection:* TDD is a process, not a test coverage strategy; can adopt later as needed.

---

## 📊 Impact Analysis

### 🟢 Positive Impacts

* **Clear measurement baseline**: Coverage targets enable tracking progress over time
* **Improved code quality**: Comprehensive testing catches bugs before release
* **Better documentation**: Tests serve as living documentation of expected behavior
* **Faster onboarding**: New developers understand testing standards immediately
* **CI/CD confidence**: Automated tests provide safety net for changes

### 🔴 Negative Impacts / Trade-offs

* **Maintenance burden**: Tests require updates when code changes
* **False positives**: Poorly written tests can mask real bugs
* **Test bloat**: Over-testing can create redundant coverage
* **Slower development**: Writing tests before/alongside features

### 🟡 Risk Mitigation

* **Regular test refactoring**: Schedule dedicated time for test maintenance
* **Test quality gates**: Use test reliability metrics alongside coverage
* **Coverage reporting**: Generate detailed reports with heatmaps
* **Test documentation**: Document test purpose and coverage gaps

---

## 🔍 Verification

### Current Test Inventory

**Unit Tests (227 tests):**
- ✅ `tests/unit/test_engines.py` - Engine unit tests (11 tests)
- ✅ `tests/unit/test_tasks.py` - Task tests (26 tests)
- ✅ `tests/unit/test_benchmarks.py` - Benchmark tests (45 tests)
- ✅ `tests/unit/test_results.py` - Results and metrics tests (44 tests)

**Integration Tests:**
- ✅ `tests/integration/test_api.py` - API integration tests (36 tests)
- ✅ `tests/integration/test_db.py` - Database integration tests (30 tests)

**E2E Tests:**
- ✅ `tests/e2e/integration/ui/test_challenges.js`
- ✅ `tests/e2e/integration/ui/test_dom.js`
- ✅ `tests/e2e/integration/ui/test_models.js`
- ✅ `tests/e2e/integration/ui/test_results.js`
- ✅ `tests/e2e/integration/ui/test_state.js`
- ✅ `tests/e2e/tests/test_dashboard.py` - Dashboard tests (35 tests)

**Shared Fixtures:**
- ✅ `tests/utils/fixtures.py` - Shared test fixtures

### Coverage Tools Available

- **pytest** - Core testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage measurement
- **httpx** - Async HTTP client for mocking
- **playwright** - Browser automation
- **vitest** - Fast unit/test runner for UI

### Fixtures Provided

- `mock_engine` - Mock engine for testing
- `mock_judge` - Mock judge for testing
- `sample_corpus` - Sample corpus data
- `sample_tasks` - Sample task definitions
- `sample_engines` - Sample engine configurations
- `sample_results` - Sample result data
- `tmp_corpus_dir` - Temporary corpus directory
- `tmp_tasks_dir` - Temporary tasks directory
- `mock_config` - Mock benchmark configuration
- `async_client` - Async HTTP client

---

## 📝 Next Steps

1. **Review and approve** - Stakeholder sign-off on coverage goals
2. **Update CI/CD** - Configure coverage thresholds in CI pipeline
3. **Generate baseline** - Run coverage tool to establish current baseline
4. **Monitor progress** - Regular coverage reporting and trend analysis
5. **Iterate** - Adjust goals based on actual coverage and bug rates

---

*(Continue with the standard ADR template content below this summary.)*
