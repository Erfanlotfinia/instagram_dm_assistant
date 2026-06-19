from pathlib import Path

import pytest


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "frontend" / "src").is_dir() and (parent / "backend" / "app").is_dir():
            return parent
    return here.parents[3]


REPO_ROOT = _repo_root()


def test_frontend_competitive_pages_render_core_labels():
    onboarding_path = REPO_ROOT / "frontend/src/pages/OnboardingPage.tsx"
    if not onboarding_path.is_file():
        pytest.skip("Frontend sources are unavailable in this runtime")

    onboarding = onboarding_path.read_text(encoding="utf-8")
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


def test_attribute_dictionary_route_replaces_fashion_dictionary():
    routes = (REPO_ROOT / "frontend/src/routes/AppRoutes.tsx").read_text(encoding="utf-8")
    page = (REPO_ROOT / "frontend/src/pages/AttributeDictionaryPage.tsx").read_text(encoding="utf-8")

    assert 'path="attributes" element={<AttributeDictionaryPage />}' in routes
    assert "/catalog/attributes" in routes
    assert 'title="Attribute dictionary"' in page
    assert "Legacy Dictionary" not in page
