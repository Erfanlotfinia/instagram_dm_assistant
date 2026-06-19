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
    analytics_overview = (REPO_ROOT / "frontend/src/pages/AnalyticsOverviewPage.tsx").read_text(encoding="utf-8")
    unavailable_demand = (REPO_ROOT / "frontend/src/pages/UnavailableDemandPage.tsx").read_text(encoding="utf-8")
    conversation = (REPO_ROOT / "frontend/src/pages/ConversationDetailPage.tsx").read_text(encoding="utf-8")
    orders = (REPO_ROOT / "frontend/src/pages/OrdersPage.tsx").read_text(encoding="utf-8")

    assert "Onboarding checklist" in onboarding
    assert "DM Simulator" in simulator
    assert "Suggested reply" in simulator
    assert "Conversion funnel" in analytics_overview
    assert "Unavailable demand" in unavailable_demand
    suggested_reply_panel = (
        REPO_ROOT / "frontend/src/components/conversations/SuggestedReplyPanel.tsx"
    ).read_text(encoding="utf-8")
    assert "SuggestedReplyPanel" in conversation
    assert "Approve and send" in suggested_reply_panel
    assert "Orders" in orders


def test_attribute_dictionary_route_replaces_fashion_dictionary():
    routes = (REPO_ROOT / "frontend/src/routes/AppRoutes.tsx").read_text(encoding="utf-8")
    nav_config = (REPO_ROOT / "frontend/src/components/shell/navConfig.tsx").read_text(encoding="utf-8")
    page = (REPO_ROOT / "frontend/src/pages/AttributeDictionaryPage.tsx").read_text(encoding="utf-8")

    assert 'path="attributes" element={<AttributeDictionaryPage />}' in routes
    assert "/catalog/attributes" in nav_config
    assert 'title="Attribute dictionary"' in page
    assert "Legacy Dictionary" not in page
