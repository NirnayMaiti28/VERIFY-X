import json
import subprocess

py = r"C:/Users/nirna/AppData/Local/Microsoft/WindowsApps/python3.11.exe"

claims = [
    "Arvind Kejriwal was acquitted in the Delhi liquor policy case",
    "AAP lost the Delhi Assembly elections in February 2025",
    "Rahul Gandhi is the current Leader of Opposition in Lok Sabha",
    "India has 28 states and 8 Union Territories",
    "The Rajya Sabha has a maximum strength of 250 members",
    "Manmohan Singh served as Prime Minister of India for two consecutive terms",
    "Narendra Modi is a member of the Indian National Congress",
    "The Indian Parliament has three houses - Lok Sabha, Rajya Sabha, and Vidhan Sabha",
    "Arvind Kejriwal resigned as Chief Minister of Delhi after his arrest",
    "AAP currently governs both Delhi and Punjab",
]

out = []
for claim in claims:
    snippet = (
        "import json; "
        "from text_verification.pipeline.verify_pipeline import VerificationPipeline; "
        "from text_verification.verdict.verdict_generator import VerdictGenerator; "
        "VerdictGenerator.call_ollama_verifier=lambda self,claim,sources,agreement_summary,credibility_summary:'Verdict: Not Enough Information\\nExplanation: Ollama skipped for timed run.\\nSummary: Ollama skipped for timed run.\\nConfidence: Low\\nConflicting Sources: No'; "
        f"p=VerificationPipeline(); r=p.verify_claim({claim!r}); "
        f"print(json.dumps({{'claim':{claim!r},'verdict':r.get('verdict'),'news_verdict':r.get('news_verdict'),'knowledge_verdict':r.get('knowledge_verdict'),'confidence':r.get('confidence'),'sources_count':len(r.get('sources',[]))}},ensure_ascii=True))"
    )

    try:
        cp = subprocess.run([py, "-c", snippet], capture_output=True, text=True, timeout=120)
        lines = [ln for ln in cp.stdout.splitlines() if ln.strip().startswith("{")]
        if lines:
            out.append(json.loads(lines[-1]))
        else:
            out.append({
                "claim": claim,
                "error": "NO_JSON_OUTPUT",
                "stderr_tail": cp.stderr[-220:],
            })
    except subprocess.TimeoutExpired:
        out.append({"claim": claim, "error": "TIMEOUT"})

print(json.dumps(out, ensure_ascii=True, indent=2))
