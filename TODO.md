1. openrouter model buttons

The /openrouter function may return a list of sub matches when it isn't an exact match, it should instead return buttons (using `reply_markup`) so the user can just select the right one with a button.

Additionally some models are a substring of another one and there is no way currently to select that substring one because it is always seen as ambigious because it could be a partial on the longer string.