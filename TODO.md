# TODO

## Completed ✅

### 1. openrouter model buttons (v1.5.0)
The /openrouter function may return a list of sub matches when it isn't an exact match, it should instead return buttons (using `reply_markup`) so the user can just select the right one with a button.

Additionally some models are a substring of another one and there is no way currently to select that substring one because it is always seen as ambigious because it could be a partial on the longer string.

**Status**: ✅ Implemented in v1.5.0 - Now uses interactive buttons for model selection

---

## Current Work Items

### High Priority

1. **Streaming Responses**
   - Implement real-time response streaming
   - Progressive message updates
   - Better UX for long responses

2. **Enhanced Image Handling**
   - Support multiple images per message
   - Image URL support
   - Better error handling

3. **Conversation Management**
   - Named conversation threads
   - Save/load history
   - Export conversations

### Medium Priority

4. **User Preferences**
   - Per-user default settings
   - Custom system prompts
   - Persistent preferences

5. **Rate Limiting & Quotas**
   - Per-user rate limits
   - Usage tracking
   - Fair usage policies

### Technical Debt

6. **Code Quality**
   - Add unit tests
   - Refactor monolithic script
   - Add type hints
   - Implement proper logging

7. **Documentation**
   - API documentation
   - Deployment guide
   - Contributing guidelines

---

For the complete feature roadmap and long-term plans, see [roadmap.md](roadmap.md)