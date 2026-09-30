"""
Real V1 Runtime — full LLM verification.
Uses compatible policy IDs so both OpenAI RAG LLM and NVIDIA Agent LLM are exercised.
"""
import os, sys, json, time, traceback
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

import yaml
from adapters.runtime_adapter import RuntimeAdapter
from services.integrated_pipeline import run_integrated_pipeline
from rag.normalization.input_normalizer import normalize_claim_input
from rag.query_builder.query_builder import QueryBuilder
from rag.retrieval.exact_matcher import ExactMatcher
from rag.embeddings.bge_embedder import BGEEmbedder
from rag.retrieval.faiss_retriever import FAISSRetriever
from rag.retrieval.bm25_retriever import BM25Retriever
from rag.retrieval.candidate_pool import CandidatePool
from rag.reranking.bge_reranker import BGEReranker
from rag.aggregation.policy_aggregator import PolicyAggregator
from rag.analyzer.deterministic_analyzer import DeterministicAnalyzer
from rag.evidence.evidence_builder import EvidenceBuilder
from rag.llm.llm_client import LLMClient
from rag.llm.prompt_builder import PromptBuilder
from rag.validation.output_validator import OutputValidator
from decision.schemas import DecisionOutcome
from decision.llm_provider import NVIDIAProvider

def mask(s, show=6):
    s = str(s) if s else "(none)"
    return s[:show] + "..." + s[-4:] if len(s) > show + 4 else "***"

def sep(t): print(f"\n{'='*72}\n  {t}\n{'='*72}")

# ── Load infrastructure ──────────────────────────────────────────────────
sep("Infrastructure load")
with open("config/config.yaml") as f:
    config = yaml.safe_load(f)

with open(config["paths"]["processed_chunks"]) as f:
    all_chunks = json.load(f)
all_chunks_dict = {c["chunk_id"]: c for c in all_chunks}

llm_key = os.getenv("LLM_API_KEY", "")
nv_key  = os.getenv("NVIDIA_API_KEY", "")
print(f"RAG LLM key : {mask(llm_key)}  mock={llm_key.lower().startswith('mock') or not llm_key}")
print(f"NVIDIA key  : {mask(nv_key)}  present={bool(nv_key and nv_key.strip())}")
print(f"Chunks      : {len(all_chunks)}")

t0 = time.time()
exact_matcher = ExactMatcher(all_chunks)
embedder = BGEEmbedder(model_name=config["embedding_model"], device=config["device"], cache_dir=config["paths"]["cache"])
faiss_retriever = FAISSRetriever(index_dir=config["paths"]["vector_store"])
faiss_retriever.load()
bm25_retriever = BM25Retriever(index_path=os.path.join(config["paths"]["vector_store"], "bm25.pkl"))
bm25_retriever.load()
reranker = BGEReranker(model_name=config["reranker_model"], device=config["device"], cache_dir=config["paths"]["cache"])
llm_client = LLMClient()
nvidia_provider = NVIDIAProvider()

def make_components():
    return {
        "config": {"candidate_pool_size": 10},
        "all_chunks": all_chunks, "all_chunks_dict": all_chunks_dict,
        "exact_matcher": exact_matcher, "bge_embedder": embedder,
        "faiss_retriever": faiss_retriever, "bm25_retriever": bm25_retriever,
        "candidate_pool": CandidatePool(), "bge_reranker": reranker,
        "policy_aggregator": PolicyAggregator(),
        "deterministic_analyzer": DeterministicAnalyzer(),
        "evidence_builder": EvidenceBuilder(),
        "llm_client": llm_client, "prompt_builder": PromptBuilder(),
        "output_validator": OutputValidator(), "query_builder": QueryBuilder(),
        "llm_provider": nvidia_provider,
    }

t_infra = time.time() - t0
print(f"Loaded in {t_infra:.1f}s")

# ── Scenario runner ──────────────────────────────────────────────────────
results = []

def run(name, claim, note=""):
    sep(f"SCENARIO: {name}")
    if note: print(f"  NOTE: {note}")
    print(f"  payer={claim['case_data']['clinical_metrics'].get('claim_payer')}  "
          f"policy={claim['case_data']['clinical_metrics'].get('claim_policy_id')}  "
          f"procs={claim['case_data']['procedures']}  "
          f"diags={claim['case_data']['diagnoses']}  "
          f"evidence={len(claim.get('evidence',[]))}")

    llm_client.last_fallback_reason = None
    t0 = time.time()
    try:
        res = run_integrated_pipeline(claim, make_components())
        elapsed = time.time() - t0

        rag_fb = llm_client.last_fallback_reason
        rag_st = f"FALLBACK:{rag_fb}" if rag_fb else "REAL_OPENAI"

        nv_st = "SKIPPED(no criteria)"
        if res.criterion_assessments:
            any_paths = any(a.evidence_paths for a in res.criterion_assessments.values())
            nv_errs = [e for e in (res.errors or []) if "NVIDIA" in e or "nvidia" in e.lower() or "API" in e]
            if nv_errs:
                nv_st = f"ERROR:{nv_errs[0][:50]}"
            elif any_paths:
                nv_st = "REAL_NVIDIA"
            else:
                nv_st = "DETERMINISTIC(no paths)"

        print(f"  RAG LLM       : {rag_st}")
        print(f"  NVIDIA LLM    : {nv_st}")
        print(f"  Decision      : {res.outcome.value}")
        print(f"  Policy        : {res.policy_id}")
        print(f"  Criteria      : {dict(res.criteria_results)}")
        print(f"  Latency       : {elapsed:.1f}s")
        if res.errors:
            for e in res.errors[:2]:
                print(f"  Error         : {e[:120]}")

        results.append({"scenario": name, "rag": rag_st, "nvidia": nv_st,
                         "decision": res.outcome.value, "lat": round(elapsed,1),
                         "status": "OK", "note": f"policy={res.policy_id}"})
    except Exception as exc:
        elapsed = time.time() - t0
        print(f"  EXCEPTION ({elapsed:.1f}s): {exc}")
        traceback.print_exc()
        results.append({"scenario": name, "rag": "ERR", "nvidia": "ERR",
                         "decision": "EXCEPTION", "lat": round(elapsed,1),
                         "status": "FAIL", "note": str(exc)[:80]})


# ── Build test claims from real DB data ──────────────────────────────────

# Get real linked claim from DB
adapter = RuntimeAdapter()
linked_1 = adapter.get_linked_runtime_claim("PA045", "CLM-08BC25", 1)
linked_2 = adapter.get_linked_runtime_claim("PA045", "CLM-08BC25", 2)

# Helper: override claim_policy_id to one that exists in RAG data
def with_policy(claim, policy_id):
    c = json.loads(json.dumps(claim))
    c["case_data"]["clinical_metrics"]["claim_policy_id"] = policy_id
    return c

# Helper: clear policy_id so aggregator picks best match freely
def no_policy(claim):
    return with_policy(claim, None)

# Helper: set evidence to empty (missing documentation scenario)
def no_evidence(claim):
    c = json.loads(json.dumps(claim))
    c["evidence"] = []
    return c

# Helper: add conflicting evidence
def conflicting_evidence(claim):
    c = json.loads(json.dumps(claim))
    c["evidence"].append({
        "evidence_key": "clinical_information",
        "evidence_id": "EV-CONFLICT-01",
        "source": "Conflicting Lab Report",
        "status": "contradictory",
        "confidence_score": 0.3,
        "is_ambiguous": True,
        "extracted_facts": {"evidence_type": "DIAGNOSIS", "content_reference": "Contradictory findings"},
        "unstructured_text": "Contradictory clinical findings noted."
    })
    return c


# ── Run scenarios ────────────────────────────────────────────────────────

# 1. ELIGIBLE: real DB claim + CPB-0660 (Aetna knee) — should match and evaluate
run("eligible_cpb0660",
    with_policy(linked_1, "CPB-0660"),
    "Real DB claim with RAG-compatible policy CPB-0660 (Aetna knee 27447)")

# 2. FAILED CRITERION: attempt 2 with CPB-0660 (different evidence set, 7 items)
run("failed_criterion_attempt2",
    with_policy(linked_2, "CPB-0660"),
    "Attempt 2 evidence set; may differ enough to change criteria outcome")

# 3. MISSING DOCUMENTATION: empty evidence + CPB-0660
run("missing_documentation",
    no_evidence(with_policy(linked_1, "CPB-0660")),
    "Empty evidence list → criteria should be MISSING → REQUEST_MORE_INFORMATION")

# 4. CONFLICTING EVIDENCE: add contradictory evidence + CPB-0660
run("conflicting_evidence",
    conflicting_evidence(with_policy(linked_1, "CPB-0660")),
    "Added contradictory evidence item → should trigger HUMAN_REVIEW")

# 5. UNKNOWN PAYER: set payer to one not in RAG data
unknown_payer_claim = with_policy(linked_1, None)
unknown_payer_claim["case_data"]["clinical_metrics"]["claim_payer"] = "UnknownInsurer"
run("unknown_payer", unknown_payer_claim,
    "Payer not in RAG data → aggregator should fail to match → HUMAN_REVIEW")

# 6. MULTIPLE PROCEDURES: add a second procedure
multi_proc = with_policy(linked_1, "CPB-0660")
multi_proc["case_data"]["procedures"] = ["27447", "27130"]
run("multiple_procedures", multi_proc,
    "Two procedures: knee(27447) + hip(27130); pipeline merges RAG outputs")

# 7. RAG FAILURE: request non-existent policy
run("rag_failure_bad_policy",
    with_policy(linked_1, "NONEXISTENT-POLICY-9999"),
    "Policy not in RAG data → fail closed to HUMAN_REVIEW")

# 8. NO POLICY CONSTRAINT: let aggregator pick best match freely
run("no_policy_constraint",
    no_policy(linked_1),
    "No policy_id constraint; aggregator selects best procedure-compatible match")


# ── Summary ──────────────────────────────────────────────────────────────
sep("RESULTS TABLE")
hdr = f"{'Scenario':<28} | {'RAG LLM':<30} | {'NVIDIA LLM':<22} | {'Decision':<22} | {'Lat':>6} | Status"
print(hdr)
print("-" * 140)
for r in results:
    print(f"{r['scenario']:<28} | {r['rag']:<30} | {r['nvidia']:<22} | {r['decision']:<22} | {r['lat']:>5.1f}s | {r['status']}")
    if r.get("note"):
        print(f"  └─ {r['note']}")

ok = sum(1 for r in results if r["status"] == "OK")
print(f"\n{ok}/{len(results)} scenarios completed without exceptions")
print(f"Infrastructure load: {t_infra:.1f}s (one-time)")
