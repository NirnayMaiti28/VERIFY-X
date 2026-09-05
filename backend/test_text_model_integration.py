import asyncio

from app.models.text_model import TextModelInterface
from app.schemas.evidence import EvidenceItem


async def main():
    model = TextModelInterface()
    # Force local mode for the test
    model.settings.model_mode = "local"
    model.settings.text_base_model = "Qwen/Qwen2.5-0.5B"
    model.settings.text_adapter = None
    
    evidence = [
        EvidenceItem(
            evidence_id="1",
            source="Test",
            title="Test",
            url="http://test.com",
            passage="Derrick Rose is a basketball player.",
            relevance_score=0.9
        )
    ]
    
    result = await model.predict("Derrick Rose is a sports player.", evidence)
    print("Result:", result)

if __name__ == '__main__':
    asyncio.run(main())
