# Phase 0 Risk Register (Top 10)

Each item is a production blocker or high‑risk gap for 10K+ users.

1. SQLite default and runtime `create_all` usage
   - Impact: DB locks and corruption under concurrency.
   - Evidence: `backend/config.py`, `backend/app.py`.
2. CORS wildcard for all API routes
   - Impact: token abuse and CSRF‑adjacent risks.
   - Evidence: `backend/app.py`.
3. Admin access uses default secret and no role model
   - Impact: unauthorized admin access if not overridden.
   - Evidence: `backend/config.py`, `backend/routes/admin.py`.
4. Tokens stored in localStorage
   - Impact: XSS exfiltration risk.
   - Evidence: `app.html`, `admin.html`.
5. Client‑supplied file paths used for uploads
   - Impact: file disclosure and data exfiltration.
   - Evidence: `backend/routes/posts.py`.
6. OAuth PKCE verifier stored in memory
   - Impact: OAuth failures in multi‑worker/multi‑instance deployments.
   - Evidence: `backend/routes/platforms.py`.
7. Long external API calls in request threads
   - Impact: worker starvation and latency spikes.
   - Evidence: `backend/routes/platforms.py`, `backend/routes/posts.py`.
8. Session revocation not enforced on protected routes
   - Impact: logout does not invalidate active tokens across endpoints.
   - Evidence: `backend/routes/auth.py`, other `@jwt_required()` routes.
9. OAuth tokens stored in plaintext
   - Impact: breach risk without encryption at rest.
   - Evidence: `backend/models.py`.
10. AI provider dependency mismatch
   - Impact: runtime errors or silent feature failures.
   - Evidence: `backend/routes/ai.py`, `backend/requirements.txt`.
