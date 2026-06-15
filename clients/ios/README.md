# iOS app (reserved)

Not started yet. Priority order: Android TV first, then this.

The original WebView-wrapper concept for iOS lives in
[`docs/plans/native_app_plan.md`](../../docs/plans/native_app_plan.md). That
approach (WKWebView around the PWA) is still valid for **iPhone/iPad** where the
web UI works well. The native **Android TV** app deliberately does **not** use a
WebView, because a 10-foot D-pad UI (Netflix/Jellyfin feel) is not achievable in
a TV browser.

When this starts, reuse the same contract: `clients/shared/openapi/`,
playback-focused, no admin tools.

