from typing import Dict, Any

class PromptBuilder:
    def __init__(self):
        pass
        
    def build_prompt(self, claim_input: Dict[str, Any], evidence_object: Dict[str, Any]) -> str:
        """
        Build the prompt for the LLM client, passing input claim and grounded evidence context.
        """
        prompt = f"""
Incoming Prior Authorization Request Claim:
{claim_input}

Retrieved Grounded Policy Evidence (Source Policy: {evidence_object['policy_id']}, Payer: {evidence_object['payer']}):
Criteria Chunks:
{evidence_object['criteria']}

Documentation Requirements:
{evidence_object['documentation']}

Exclusions extracted:
{evidence_object['exclusions']}

INSTRUCTIONS:
1. Synthesize the above policy context and output the final prioritized information in the target JSON schema.
2. The output JSON schema must strictly contain only the following root keys:
   - "claim_id": (string matching the claim)
   - "policy_matches": (array containing policy matches with keys: policy_id, payer, relevance_score)
   - "criteria": (array of clinical requirements containing keys: criterion_id, criterion, policy_requirement, source)
   - "documentation_requirements": (array containing keys: requirement, source)
3. Under "criteria", populate "criterion" with the specific title/area of criteria, and "policy_requirement" with the strict verbatim clinical condition details from the policy context.
4. ABSOLUTE PROHIBITION: You are NOT a coverage decision engine. You must NEVER include any outcome decisions (such as "APPROVE", "REJECT", "DENY", "PEND", "MET", "NOT_MET", "ELIGIBLE", "INELIGIBLE", "COVERED", "NOT_COVERED").
5. Do NOT hallucinate policy criteria or documentation. Only include what is explicitly present in the provided evidence.

Target JSON Format:
{{
  "claim_id": "string",
  "policy_matches": [
    {{
      "policy_id": "string",
      "payer": "string",
      "relevance_score": float
    }}
  ],
  "criteria": [
    {{
      "criterion_id": "string",
      "criterion": "string",
      "policy_requirement": "string",
      "source": {{
        "policy_id": "string",
        "section": "string"
      }}
    }}
  ],
  "documentation_requirements": [
    {{
      "requirement": "string",
      "source": "string"
    }}
  ]
}}
"""
        return prompt
