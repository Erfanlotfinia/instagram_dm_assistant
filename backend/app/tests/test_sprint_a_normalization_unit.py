from types import SimpleNamespace
from uuid import uuid4

from app.services.fashion_normalization import ColorNormalizer, SizeNormalizer


def test_color_normalizer_persian_and_english_defaults():
    normalizer = ColorNormalizer()
    assert normalizer.normalize(None, " مشکی!! ").normalized_value == "black"
    assert normalizer.normalize(None, "black").source == "global_alias"


def test_color_normalizer_shop_alias_override(monkeypatch):
    shop_id = uuid4()
    normalizer = ColorNormalizer()

    def fake_alias(request_shop_id, cleaned, *, shop_only):
        if request_shop_id == shop_id and shop_only and cleaned == "آبی":
            return SimpleNamespace(normalized_value="navy")
        return None

    monkeypatch.setattr(normalizer, "_alias", fake_alias)
    result = normalizer.normalize(shop_id, "آبی")
    assert result.normalized_value == "navy"
    assert result.source == "shop_alias"


def test_size_normalizer_persian_numeric_and_free_size():
    normalizer = SizeNormalizer()
    assert normalizer.normalize(None, "ال").normalized_value == "L"
    assert normalizer.normalize(None, "سایز ۳۸").normalized_value == "38"
    assert normalizer.normalize(None, "فری‌سایز").normalized_value == "FREE"
