def build_hero(ctx, meta):
    return {"type": "hero", "title": ctx.get("title"), "meta": meta}


def build_features(ctx, meta):
    return {"type": "features", "items": ctx.get("features", []), "meta": meta}


def build_pricing(ctx, meta):
    return {"type": "pricing", "plans": ctx.get("plans", []), "meta": meta}


def build_faq(ctx, meta):
    return {"type": "faq", "entries": ctx.get("faq", []), "meta": meta}


def build_testimonials(ctx, meta):
    return {"type": "testimonials", "quotes": ctx.get("quotes", []), "meta": meta}


SECTION_BUILDERS = {
    "hero": build_hero,
    "features": build_features,
    "pricing": build_pricing,
    "faq": build_faq,
    "testimonials": build_testimonials,
}

SECTION_META = {
    "hero": {"max_blocks": 3},
    "features": {"max_blocks": 6},
    "pricing": {"max_blocks": 4},
}


def render_section(name, ctx):
    meta = SECTION_META.get(name)
    if meta is None:
        return None
    return SECTION_BUILDERS[name](ctx, meta)
