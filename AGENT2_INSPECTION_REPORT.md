# Agent 2 Inspection & Gap Analysis Report

**Date**: Phase 2 Completion → Agent 2 Refactoring Initiation  
**Scope**: Systematic review of agent2/ module against frozen V1 architecture requirements  
**Status**: Implementation-Ready (gaps identified, refactoring path clear)

---

## 1. CURRENT IMPLEMENTATION STATE

### 1.1 Module Structure Exists But Incomplete
- **Module Directories**: database/, retrieval/, reasoning/, submission/, payer/, audit/, schemas/, tests/, workflow/
- **Critical Gap**: NO `__init__.py` files in any subdirectory
  - Causes ModuleNotFoundError when importing (e.g., `from database.db_manager import ...`)
  - Blocks all test execution
  - Prevents proper Python package structure

### 1.2 Database Layer (Partial Implementation)
**File**: [agent2/database/db_manager.py](agent2/database/db_manager.py)  
**Status**: ✓ Schema defined, ✗ Test coverage minimal

- **Implemented**: SQLite schema with patients, conditions, medications, observations, procedures, encounters, documents
- **Implemented**: Claims tracking with version history (claim_versions table for immutability)
- **Missing**: 
  - Evidence state tracking (FOUND vs MISSING distinction not in schema)
  - Recovery attempt history
  - Agent 1 interaction metadata

### 1.3 Schemas (Contracts Defined But Not Fully Aligned)
**Files**: [agent2/schemas/claim.py](agent2/schemas/claim.py), [agent2/schemas/submission.py](agent2/schemas/submission.py), [agent2/schemas/payer_response.py](agent2/schemas/payer_response.py)

**Issues Identified**:
1. **CanonicalClaim Mismatch**: Agent 2 version has different structure than V1
   - V1: `case_data`, `evidence` list (see [decision/schemas.py](decision/schemas.py))
   - Agent 2: `claim_id`, `claim_version`, `patient_id`, `provider_id`, `payer_id`, `diagnosis`, `requested_service`
   - **Impact**: Cannot directly use V1's CanonicalClaim format

2. **PayerResponse Contract Incomplete**:
   - Missing distinction: Is REJECT recoverable or terminal?
   - Missing: Clinical rule evaluation details
   - Missing: Provenance chain back to original policy/criteria

3. **Evidence Schema**: No explicit FOUND/MISSING state
   - Current: Evidence object with source_type, content
   - Required: state field (FOUND vs MISSING) to track retrieval success/failure

### 1.4 Orchestrator Logic (Mostly Complete But Gaps Remain)
**File**: [agent2/workflow/orchestrator.py](agent2/workflow/orchestrator.py)  
**Status**: ✓ Core flow implemented, ✗ Outcome routing incomplete, ✗ No integration tests

**Implemented Decision Path**:
```
INIT → RECEIVED → VALIDATING → VALIDATED → RETRIEVING_EVIDENCE 
→ RETRIEVING_POLICY → MATCHING_CRITERIA → BUILDING_PACKAGE 
→ READY_FOR_SUBMISSION → SUBMITTED → WAITING_FOR_PAYER
```

**Outcome Routing Implemented**:
- ✓ APPROVED → Terminal (APPROVED)
- ✓ MORE_INFO → Recovery search + resubmit (if evidence recovered, increment version)
- ✓ REJECTED → Recovery search + resubmit (if recovered AND eligible, increment version)
- ✗ HUMAN_REVIEW (from Agent 1) → **NOT ROUTED** (should terminate without invoking recovery)

**Recovery Logic Issues**:
1. **Evidence Eligibility**: Hard-coded checks (e.g., statin trial duration > 90 days)
   - Should be extracted to schema/config
   - Should be delegated to deterministic analyzer (not in orchestrator)

2. **REJECT Classification**: No distinction between recoverable vs terminal REJECT
   - Currently: Treats all REJECT as potentially recoverable
   - Required: Agent 1 should indicate REJECT(hard) vs REJECT(recoverable)

3. **Version Increment**: Uses manual `version_manager.create_new_version()`
   - No immutable history validation
   - No version limit enforcement until after loop

### 1.5 Routing Gaps: Missing Cases

**Current Gaps**:
```
1. Agent 1 outcome: HUMAN_REVIEW
   Current: NOT HANDLED → falls through
   Required: Terminal state, no Agent 2 action (safety gate)

2. Agent 1 outcome: REJECT (hard/terminal)
   Current: No distinguishing from recoverable REJECT
   Required: Immediate escalation to HUMAN_REVIEW (no recovery attempt)

3. Evidence retrieval failure in recovery attempt
   Current: Escalates to HUMAN_REVIEW
   Required: Same behavior (correct, but undocumented)

4. Max resubmission limit exceeded
   Current: Escalates to HUMAN_REVIEW
   Required: Same behavior (correct, implemented)
```

### 1.6 Evidence State Tracking (Missing)

**Required Distinction**:
- **FOUND**: Evidence successfully retrieved and parsed
- **MISSING**: Evidence searched for but not found in database

**Current State**:
- Evidence is retrieved or not retrieved
- No explicit state field in schema
- Recovery logic conflates "evidence retrieved" with "evidence eligibility confirmed"

### 1.7 Audit Logging (Implemented But Incomplete)
**File**: [agent2/audit/audit_logger.py](agent2/audit/audit_logger.py)  
**Status**: ✓ Basic implementation, ✗ Schema and retention policies unclear

**Implemented**:
- log_transition(claim_id, version, from_state, to_state, operation, result, error)

**Missing**:
- Bounded retention policy (e.g., keep last 100 transitions)
- Integration with version manager
- Correlation tracking across recovery attempts

### 1.8 Test Coverage (None)
**Files**: [agent2/tests/test_end_to_end.py](agent2/tests/test_end_to_end.py), [agent2/tests/setup_test_data.py](agent2/tests/setup_test_data.py)

**Issues**:
1. Test files exist but cannot be imported
2. No __init__.py → ModuleNotFoundError
3. No unit tests for individual components
4. End-to-end test assumes Gemini API availability

---

## 2. FROZEN V1 ARCHITECTURE REQUIREMENTS

**Requirements from conversation history (Phase 2 completion)**:

### 2.1 Evidence & Criterion Distinction
```
Evidence States (Retrieval Result):
- FOUND: Evidence exists in database, successfully parsed
- MISSING: Evidence not found in database

Criterion States (Policy Evaluation):
- SATISFIED: Clinical evidence meets policy criterion
- NOT_SATISFIED: Clinical evidence fails to meet criterion
- UNCERTAIN: Evidence exists but eligibility/applicability unclear
```

### 2.2 Recovery Routing (Deterministic)
```
Agent 1 Decision → Agent 2 Action:

APPROVE → Terminal
  - Escalate success upstream
  - No Agent 2 action
  - Status: APPROVED

REQUEST_MORE_INFORMATION → Recovery Search
  - Parse Agent 1 requested_information
  - Search provider database for matching evidence
  - If FOUND: Create new version, resubmit
  - If MISSING: HUMAN_REVIEW (genuine gap)
  - Status: WAITING_FOR_PAYER (loop) or HUMAN_REVIEW (terminal)

REJECT → Assess Recoverability
  - If rejection reason indicates missing evidence (recoverable):
    - Parse failed_criteria
    - Search provider database
    - If recovered: Create new version, resubmit
    - If MISSING: HUMAN_REVIEW
  - If rejection reason indicates clinical ineligibility (hard):
    - Escalate to HUMAN_REVIEW (no recovery attempt)
  - Status: WAITING_FOR_PAYER (loop) or HUMAN_REVIEW (terminal)

HUMAN_REVIEW → Terminal (Safety Gate)
  - Do NOT invoke Agent 2 recovery
  - Escalate as-is to human workflow
  - Status: HUMAN_REVIEW (terminal)
```

### 2.3 SubmissionPackage Building (Minimum-Necessary)
```
Requirements:
- Include only evidence referenced in criterion_evals
- Exclude candidate evidence not used for decision
- Preserve evidence provenance (source_type, content, evidence_id)
- Maintain trust boundary (patient_reference is anonymized)
```

### 2.4 Version Management & Immutability
```
Requirements:
- claim_versions table stores immutable JSON snapshots
- Each resubmission increments claim_version
- Version limit: MAX_RESUBMISSION_ATTEMPTS (currently 3)
- Exceeding limit → HUMAN_REVIEW (terminal)
- Version history preserved for audit trail
```

### 2.5 No Direct Payer DB Access
```
Frozen Constraint:
- Agent 2 reads ONLY from provider database (agent2.db)
- Agent 2 reads from payer_data.db ONLY via Agent 1 response
- Current Status: ✓ Implemented (Agent 2 never accesses payer_data.db)
```

### 2.6 LLM Role (Non-Decisional)
```
Constraint:
- LLM provides evidence mapping and criterion assessment
- Deterministic engine makes final outcome decision
- Current Status: ✓ Implemented (criterion_mapper uses Gemini for mapping)
```

---

## 3. GAP ANALYSIS

### 3.1 Critical Gaps (Blocking Implementation)

| Gap | Location | Impact | Priority |
|-----|----------|--------|----------|
| Module __init__.py missing | agent2/**/__init__.py | Cannot import modules, tests fail | CRITICAL |
| Evidence state tracking missing | schemas/evidence.py | Cannot distinguish FOUND/MISSING | CRITICAL |
| HUMAN_REVIEW routing missing | orchestrator.py | Agent 2 acts on human review output | HIGH |
| REJECT recoverability classification missing | schemas/payer_response.py | Cannot differentiate terminal vs recoverable | HIGH |

### 3.2 High-Priority Gaps

| Gap | Location | Impact | Fix Effort |
|-----|----------|--------|-----------|
| CanonicalClaim schema mismatch | schemas/claim.py | Cannot use V1 claims directly | Medium (adapter) |
| No integration tests | tests/ | Cannot validate end-to-end flow | High (20+ tests) |
| Routing logic untested | orchestrator.py | MORE_INFO/REJECT loops untested | High (needs fixtures) |
| Version manager untested | submission/version_manager.py | Claim versioning not validated | Medium (5+ tests) |

### 3.3 Medium-Priority Gaps

| Gap | Location | Impact | Fix Effort |
|-----|----------|--------|-----------|
| Audit logging schema undefined | audit/audit_logger.py | No bounded retention guarantees | Low (schema doc) |
| Evidence eligibility hard-coded | orchestrator.py | Cannot generalize to other policies | Medium (extract rules) |
| Recovery concept mapping hard-coded | reasoning/rejection_analyzer.py | Only works for LDL/Statin/HbA1c | Medium (generalize) |

---

## 4. IMPLEMENTATION ROADMAP

### Phase 1: Foundation Fixes (No Logic Changes)
**Goal**: Make Agent 2 importable and testable

1. ✅ Create agent2/__init__.py (empty)
2. ✅ Create agent2/database/__init__.py (empty)
3. ✅ Create agent2/retrieval/__init__.py (empty)
4. ✅ Create agent2/reasoning/__init__.py (empty)
5. ✅ Create agent2/schemas/__init__.py (empty)
6. ✅ Create agent2/submission/__init__.py (empty)
7. ✅ Create agent2/payer/__init__.py (empty)
8. ✅ Create agent2/audit/__init__.py (empty)
9. ✅ Create agent2/workflow/__init__.py (empty)
10. ✅ Create agent2/validators/__init__.py (empty)
11. ✅ Create agent2/tests/__init__.py (empty)
12. ✅ Verify tests import without ModuleNotFoundError

### Phase 2: Contract Alignment (Schemas)
**Goal**: Make Agent 2 contracts compatible with V1 patterns

1. Add Evidence.state field (FOUND/MISSING)
2. Add PayerResponse.is_recoverable flag (or parse from reason)
3. Document CanonicalClaim mapping between V1 and Agent 2 versions
4. Update criterion evaluation to use V1 decision outcome terminology

### Phase 3: Routing Logic Completion
**Goal**: Handle all Agent 1 outcomes correctly

1. Add HUMAN_REVIEW → Terminal routing (no recovery)
2. Add REJECT(hard) detection and routing
3. Add REJECT(recoverable) → recovery attempt → resubmit
4. Document recovery attempt limit enforcement

### Phase 4: Comprehensive Testing
**Goal**: Validate all paths

1. Unit tests for each component (database, retrieval, reasoning, submission, audit)
2. Integration tests for:
   - APPROVE → Terminal
   - MORE_INFO → Recovery → Resubmit → APPROVE/HUMAN_REVIEW
   - REJECT(recoverable) → Recovery → Resubmit → APPROVE/HUMAN_REVIEW
   - REJECT(hard) → HUMAN_REVIEW (no recovery)
   - HUMAN_REVIEW → Terminal (no recovery)
   - Max version limit → HUMAN_REVIEW
3. Regression tests: Verify 166 V1 tests still passing

### Phase 5: Integration (Deferred Per User Request)
**Goal**: Connect Agent 2 to V1 workflow

- Integrate Agent 2 orchestrator with services/integrated_pipeline.py
- Route Agent 1 outcomes to Agent 2 for recovery attempts
- **Note**: NOT in current scope (user deferred this)

---

## 5. FILES REQUIRING CHANGES

### Core Changes (Phase 1-3)
1. Create `agent2/__init__.py` (empty package marker)
2. Create `agent2/*/__init__.py` for all subdirectories
3. Update `agent2/schemas/evidence.py` - add state field
4. Update `agent2/schemas/payer_response.py` - add is_recoverable flag
5. Update `agent2/workflow/orchestrator.py` - add HUMAN_REVIEW routing
6. Update `agent2/submission/version_manager.py` - enforce version limits
7. Update `agent2/reasoning/rejection_analyzer.py` - make concept mapping generizable

### Test Files (Phase 4)
1. Create `agent2/tests/__init__.py`
2. Rewrite `agent2/tests/test_end_to_end.py` - fix imports
3. Add `agent2/tests/test_orchestrator_routing.py` - outcomes routing
4. Add `agent2/tests/test_evidence_retrieval.py` - evidence state tracking
5. Add `agent2/tests/test_package_building.py` - minimal evidence validation
6. Add `agent2/tests/test_version_management.py` - versioning limits

### Verification (Phase 5)
1. Run all Agent 2 tests → All passing
2. Run all V1 tests → 166 still passing
3. Generate test coverage report

---

## 6. VALIDATION CRITERIA

### Success Metrics
- ✓ All agent2/ modules import without errors
- ✓ agent2/tests/ runs without import failures
- ✓ Routing logic handles all 5 Agent 1 outcomes (APPROVE, MORE_INFO, REJECT×2, HUMAN_REVIEW)
- ✓ Evidence tracking distinguishes FOUND vs MISSING states
- ✓ Version limits enforced (max 3 resubmissions)
- ✓ 166 V1 tests still passing (no regression)
- ✓ New Agent 2 tests cover critical paths (20+ tests)

### Test Coverage by Path
```
MORE_INFO Flow (2 tests):
  - Agent 1 responds MORE_INFO → Evidence recovered → Resubmit → SUCCESS
  - Agent 1 responds MORE_INFO → Evidence MISSING → HUMAN_REVIEW

REJECT(Recoverable) Flow (2 tests):
  - Agent 1 responds REJECT → Evidence recovered AND eligible → Resubmit → SUCCESS
  - Agent 1 responds REJECT → Evidence recovered BUT ineligible → HUMAN_REVIEW

REJECT(Hard) Flow (1 test):
  - Agent 1 responds REJECT(hard) → HUMAN_REVIEW (no recovery)

HUMAN_REVIEW Flow (1 test):
  - Agent 1 responds HUMAN_REVIEW → HUMAN_REVIEW (terminal, no Agent 2 action)

APPROVE Flow (1 test):
  - Agent 1 responds APPROVE → APPROVED (terminal)

Version Limit Flow (1 test):
  - More than 3 resubmissions attempted → HUMAN_REVIEW (terminal)
```

---

## 7. CONCLUSION

Agent 2 has a solid architectural foundation with most components implemented. The critical issues are:

1. **Python package structure** (BLOCKER) - Missing __init__.py files
2. **Evidence state tracking** (MISSING) - FOUND vs MISSING distinction not in schema
3. **Routing completeness** (INCOMPLETE) - HUMAN_REVIEW outcome not handled
4. **Test coverage** (NONE) - No passing tests due to import failures

**Implementation path is clear**: Fix foundation (Phase 1), align schemas (Phase 2), complete routing (Phase 3), add tests (Phase 4).

**Estimated effort**: 8-12 hours for Phases 1-4, deferred integration per user request.

---

## Appendix: File Reference Map

### Agent 2 Structure
```
agent2/
  __init__.py                          [MISSING]
  database/
    __init__.py                        [MISSING]
    db_manager.py                      ✓ Schema defined
    importer.py                        (Not reviewed)
    repositories/
      __init__.py                      [MISSING]
      claim_repository.py              (Not reviewed)
      patient_repository.py            (Not reviewed)
  retrieval/
    __init__.py                        [MISSING]
    patient_retriever.py               (Not reviewed)
    policy_retriever.py                (Not reviewed)
    evidence_ranker.py                 (Not reviewed)
  reasoning/
    __init__.py                        [MISSING]
    criterion_mapper.py                (Not reviewed)
    rejection_analyzer.py              ⚠ Concept mapping hard-coded
  schemas/
    __init__.py                        [MISSING]
    claim.py                           ⚠ Mismatch with V1
    evidence.py                        ⚠ Missing state field
    submission.py                      ✓ Mostly aligned
    payer_response.py                  ⚠ Missing is_recoverable
  submission/
    __init__.py                        [MISSING]
    package_builder.py                 ✓ Trust boundary enforced
    boundary_filter.py                 (Not reviewed)
    version_manager.py                 ⚠ Version limits not enforced
  payer/
    __init__.py                        [MISSING]
    agent1_client.py                   ✓ Correct trust boundary
  audit/
    __init__.py                        [MISSING]
    audit_logger.py                    ⚠ Retention policy undefined
  workflow/
    __init__.py                        [MISSING]
    orchestrator.py                    ⚠ HUMAN_REVIEW routing missing
  validators/
    __init__.py                        [MISSING]
    (Not reviewed)
  tests/
    __init__.py                        [MISSING]
    test_end_to_end.py                 ✗ Import failures
    setup_test_data.py                 (Not reviewed)
```

### V1 Reference Files
- [decision/schemas.py](decision/schemas.py) - DecisionOutcome, CanonicalClaim
- [decision/agent.py](decision/agent.py) - Agent 1 evaluation
- [services/integrated_pipeline.py](services/integrated_pipeline.py) - V1 workflow
- [adapters/runtime_adapter.py](adapters/runtime_adapter.py) - Payer data access pattern
