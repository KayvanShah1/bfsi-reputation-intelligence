from __future__ import annotations

from bri_engine.core.schemas import MentionClassification
from bri_engine.settings import Settings, get_settings


TAXONOMY = """
Allowed taxonomy:

1. Brand Perception
- Thought Leadership: CXO or expert commentary, market outlook, industry viewpoints.
- Product Strategy: launches, positioning, pricing, offers, NFOs, SIP plans.
- Brand Visibility & Marketing: campaigns, sponsorships, ambassadors, awareness initiatives.

2. User Experience
- Product & Service Quality: returns, benchmarks, reliability, product performance.
- Customer Support & Complaint Resolution: delayed redemption, KYC, support, complaints.
- Digital & Omnichannel Experience: app, website, login, onboarding, transaction screens.

3. Responsible Business Practices
- Regulatory Compliance & Ethical Governance: SEBI, compliance, disclosure, governance.
- Social Impact & Community (CSR): financial literacy, donations, outreach, community work.
"""

FEW_SHOT_EXAMPLES = """
Examples:

Mention: ICICI Prudential Mutual Fund launches a new NFO focused on energy opportunities.
Classification: Product Strategy, Neutral. The mention discusses a fund launch.

Mention: Investors complain that redemption from ICICI Prudential was delayed.
Classification: Customer Support & Complaint Resolution, Negative. The mention is about complaint handling.

Mention: ICICI Prudential AMC CIO shares his outlook on interest rates and equity markets.
Classification: Thought Leadership, Neutral. The mention is expert commentary.

Mention: Users report that the ICICI Prudential app crashes during SIP registration.
Classification: Digital & Omnichannel Experience, Negative. The mention is about app reliability.

Mention: SEBI imposes a penalty for disclosure lapses.
Classification: Regulatory Compliance & Ethical Governance, Negative. The mention is regulatory.

Mention: ICICI Prudential conducts a financial literacy programme for women investors.
Classification: Social Impact & Community (CSR), Positive. The mention is community outreach.
"""

SYSTEM_PROMPT = f"""
You classify BFSI digital mentions into a fixed reputation-intelligence taxonomy.
Use only the allowed taxonomy and return validated structured output.
Do not invent categories. Keep the rationale short and evidence-based.

{TAXONOMY}

Tie-break rules:
- Fund launches, NFOs, pricing, SIP plans, and product positioning map to Product Strategy.
- Returns, benchmark performance, NAV, and quality claims map to Product & Service Quality.
- App, website, login, onboarding, and transaction issues map to Digital & Omnichannel Experience.
- KYC, redemption delays, complaint handling, and support map to Customer Support & Complaint Resolution.
- CIO, CEO, fund manager, economist, and market outlook commentary map to Thought Leadership.
- SEBI, penalties, disclosure, governance, mis-selling, and compliance map to Regulatory Compliance.

{FEW_SHOT_EXAMPLES}
"""


def build_agent(settings: Settings | None = None):
    resolved_settings = settings or get_settings()
    api_key = resolved_settings.openrouter_api_key_value
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing.")

    from pydantic_ai import Agent
    from pydantic_ai.models.openrouter import OpenRouterModel
    from pydantic_ai.providers.openrouter import OpenRouterProvider

    model = OpenRouterModel(
        resolved_settings.openrouter_model,
        provider=OpenRouterProvider(
            api_key=api_key,
            app_title="BFSI Reputation Intelligence",
        ),
    )
    return Agent(
        model=model,
        output_type=MentionClassification,
        instructions=SYSTEM_PROMPT,
        retries=resolved_settings.openrouter_retries,
    )


def classify_mention(
    text: str,
    existing_sentiment: str | None = None,
    settings: Settings | None = None,
) -> MentionClassification:
    agent = build_agent(settings)
    prompt = f"""
Mention text:
{text}

Existing sentiment, if available:
{existing_sentiment or "Not provided"}
"""
    result = agent.run_sync(prompt)
    return result.output
