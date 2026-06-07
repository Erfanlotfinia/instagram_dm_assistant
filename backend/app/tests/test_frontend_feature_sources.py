from pathlib import Path


def test_frontend_competitive_pages_render_core_labels():
    onboarding = Path("frontend/src/pages/OnboardingPage.tsx").read_text()
    simulator = Path("frontend/src/pages/DMSimulatorPage.tsx").read_text()
    analytics = Path("frontend/src/pages/AnalyticsPage.tsx").read_text()
    conversation = Path("frontend/src/pages/ConversationDetailPage.tsx").read_text()
    orders = Path("frontend/src/pages/OrdersPage.tsx").read_text()

    assert "Onboarding checklist" in onboarding
    assert "DM Simulator" in simulator
    assert "Suggested reply" in simulator
    assert "Funnel cards" in analytics
    assert "Unavailable demand" in analytics
    assert "Approve / send edited reply" in conversation
    assert "Risk" in orders
