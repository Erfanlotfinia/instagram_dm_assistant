from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_frontend_competitive_pages_render_core_labels():
    onboarding = (REPO_ROOT / "frontend/src/pages/OnboardingPage.tsx").read_text(encoding="utf-8")
    simulator = (REPO_ROOT / "frontend/src/pages/DMSimulatorPage.tsx").read_text(encoding="utf-8")
    analytics = (REPO_ROOT / "frontend/src/pages/AnalyticsPage.tsx").read_text(encoding="utf-8")
    conversation = (REPO_ROOT / "frontend/src/pages/ConversationDetailPage.tsx").read_text(encoding="utf-8")
    orders = (REPO_ROOT / "frontend/src/pages/OrdersPage.tsx").read_text(encoding="utf-8")

    assert "Onboarding checklist" in onboarding
    assert "DM Simulator" in simulator
    assert "Suggested reply" in simulator
    assert "Funnel cards" in analytics
    assert "Unavailable demand" in analytics
    suggested_reply_panel = (
        REPO_ROOT / "frontend/src/components/conversations/SuggestedReplyPanel.tsx"
    ).read_text(encoding="utf-8")
    assert "SuggestedReplyPanel" in conversation
    assert "Approve and send" in suggested_reply_panel
    assert "Risk" in orders
