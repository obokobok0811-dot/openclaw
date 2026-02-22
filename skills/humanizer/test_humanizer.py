"""
Regression tests for the humanizer.

Each test case targets a specific AI writing pattern that has been observed
recurring despite instructions to avoid it. When a new pattern is discovered,
add a test here FIRST, then update patterns.json or humanizer.py to fix it.

Run: python -m pytest test_humanizer.py -v
"""

import pytest
from humanizer import humanize


# ---------------------------------------------------------------------------
# Stock Phrases
# ---------------------------------------------------------------------------

class TestStockPhrases:
    """Phrases AI models default to that humans rarely write."""

    def test_its_worth_noting(self):
        text = "It's worth noting that the system handles 10k requests per second. The architecture uses Redis for caching. This provides low-latency responses across all regions."
        result = humanize(text)
        assert "worth noting" not in result.lower()
        assert "10k requests" in result

    def test_at_the_end_of_the_day(self):
        text = "At the end of the day, performance matters more than elegance. The team optimized the hot path to reduce latency by 40%. Memory usage also dropped significantly."
        result = humanize(text)
        assert "at the end of the day" not in result.lower()
        assert "performance matters" in result

    def test_delve_into(self):
        text = "Let's delve into the architecture decisions behind this system. The core uses event sourcing for state management. All mutations flow through a command bus."
        result = humanize(text)
        assert "delve" not in result.lower()

    def test_navigate_the_landscape(self):
        text = "Teams must navigate the landscape of modern deployment tools carefully. Container orchestration has become standard practice. Kubernetes dominates the market."
        result = humanize(text)
        assert "navigate the landscape" not in result.lower()

    def test_leverage(self):
        text = "We can leverage this API to build the integration. The endpoint supports batch operations. Rate limits are generous for authenticated calls."
        result = humanize(text)
        assert "leverage" not in result.lower()
        assert "use" in result.lower()

    def test_utilize(self):
        text = "The system utilizes a message queue for async processing. Workers pull from the queue at their own pace. Failed messages are retried with exponential backoff."
        result = humanize(text)
        assert "utilizes" not in result.lower()
        assert "uses" in result.lower()

    def test_deep_dive(self):
        text = "This article provides a deep dive into Kubernetes networking. Pod-to-pod communication uses a flat network model. Services abstract away individual pod addresses."
        result = humanize(text)
        assert "deep dive" not in result.lower()

    def test_seamlessly(self):
        text = "The plugin integrates seamlessly with existing workflows. Installation takes under a minute. No configuration changes are needed for basic usage."
        result = humanize(text)
        assert "seamlessly" not in result.lower()

    def test_robust(self):
        text = "This provides a robust solution for handling concurrent writes. The locking mechanism prevents race conditions. Deadlock detection runs every 5 seconds."
        result = humanize(text)
        assert "robust solution" not in result.lower()
        assert "solution" in result.lower()

    def test_game_changer(self):
        text = "This feature is a game-changer for the team's productivity. Build times dropped from 12 minutes to 90 seconds. Hot reload now works across all modules."
        result = humanize(text)
        assert "game-changer" not in result.lower()

    def test_holistic_approach(self):
        text = "Taking a holistic approach to monitoring reveals patterns that point metrics miss. Distributed tracing connects frontend errors to backend causes. Log correlation adds context."
        result = humanize(text)
        assert "holistic approach" not in result.lower()

    def test_tapestry(self):
        text = "The city's history is a rich tapestry of cultural influences spanning five centuries. Dutch colonial architecture lines the waterfront. Chinese temples stand beside Portuguese churches."
        result = humanize(text)
        assert "rich tapestry" not in result.lower()

    def test_plethora(self):
        text = "There's a plethora of options for CI/CD pipelines. GitHub Actions, GitLab CI, and CircleCI each have different strengths. Cost varies significantly at scale."
        result = humanize(text)
        assert "plethora" not in result.lower()


# ---------------------------------------------------------------------------
# Performed Authenticity
# ---------------------------------------------------------------------------

class TestPerformedAuthenticity:
    """Fake enthusiasm and rapport-building phrases."""

    def test_great_question(self):
        text = "Great question! The answer depends on your traffic patterns. For under 1000 RPS, a single instance is fine. Beyond that, you'll want horizontal scaling."
        result = humanize(text)
        assert "great question" not in result.lower()
        assert "traffic patterns" in result

    def test_glad_you_asked(self):
        text = "I'm glad you asked! The migration path from v2 to v3 is straightforward. First, update the SDK. Then run the compatibility checker against your codebase."
        result = humanize(text)
        assert "glad you asked" not in result.lower()

    def test_absolutely(self):
        text = "Absolutely! You can run multiple instances behind a load balancer. Each instance maintains its own connection pool. Session affinity isn't required."
        result = humanize(text)
        assert result.strip()[0:3] != "Abs"


# ---------------------------------------------------------------------------
# Hedging Language
# ---------------------------------------------------------------------------

class TestHedging:
    """Qualifiers that weaken statements without adding information."""

    def test_important_to_remember(self):
        text = "It's important to remember that database indexes have a write cost. Each insert updates every relevant index. For write-heavy tables, be selective about what you index."
        result = humanize(text)
        assert "important to remember" not in result.lower()
        assert "database indexes" in result

    def test_essentially(self):
        text = "The proxy essentially forwards all traffic to the upstream server. It adds headers for authentication. Response caching happens at this layer."
        result = humanize(text)
        assert "essentially" not in result.lower()

    def test_arguably(self):
        text = "Rust is arguably the best choice for this workload. Its ownership model prevents the memory bugs that plague C++ services. Compile times are the main drawback."
        result = humanize(text)
        assert "arguably" not in result.lower()


# ---------------------------------------------------------------------------
# Structural Patterns
# ---------------------------------------------------------------------------

class TestStructural:
    """Formatting and structural tells of AI writing."""

    def test_em_dash_replacement(self):
        text = "The system handles failures gracefully — retrying with backoff — before alerting the on-call engineer. This approach reduces alert fatigue across the team."
        result = humanize(text)
        assert "—" not in result
        assert "–" not in result

    def test_participle_tail_removal(self):
        text = "The framework was released in 2024, highlighting the growing demand for type-safe server components."
        result = humanize(text)
        assert "highlighting" not in result
        # The factual part should remain
        assert "2024" in result

    def test_participle_tail_underscoring(self):
        text = "Revenue grew 40% year over year, underscoring the strength of the subscription model."
        result = humanize(text)
        assert "underscoring" not in result
        assert "40%" in result

    def test_participle_tail_showcasing(self):
        text = "The team shipped 12 features in Q3, showcasing their improved velocity after the reorg."
        result = humanize(text)
        assert "showcasing" not in result

    def test_emoji_in_headers(self):
        text = "## 🚀 Getting Started\n\nInstall the package with npm. Run the init command. Open the config file."
        result = humanize(text)
        assert "🚀" not in result.split("\n")[0]
        assert "## Getting Started" in result

    def test_multiple_participle_tails(self):
        text = ("Sales increased 25% in Asia, demonstrating strong regional growth. "
                "The European team signed 40 new accounts, solidifying market position. "
                "Customer retention hit 95%, reflecting the impact of the new onboarding flow.")
        result = humanize(text)
        assert "demonstrating" not in result
        assert "solidifying" not in result
        assert "reflecting" not in result
        assert "25%" in result
        assert "40 new accounts" in result
        assert "95%" in result


# ---------------------------------------------------------------------------
# Significance Inflation
# ---------------------------------------------------------------------------

class TestSignificance:
    """Words that inflate importance beyond what content supports."""

    def test_pivotal_role(self):
        text = "Caching plays a pivotal role in reducing database load. Redis stores frequently accessed queries. TTLs prevent stale data from persisting too long."
        result = humanize(text)
        assert "pivotal role" not in result.lower()

    def test_crucial_role(self):
        text = "Monitoring plays a crucial role in maintaining system reliability. Dashboards show real-time metrics. Alerts fire when thresholds are breached."
        result = humanize(text)
        assert "crucial role" not in result.lower()

    def test_truly_remarkable(self):
        text = "The truly remarkable thing about this approach is its simplicity. One config file controls the entire pipeline. No custom scripts needed."
        result = humanize(text)
        assert "truly" not in result.lower()

    def test_testament_to(self):
        text = "The system's uptime is a testament to the team's engineering discipline. Zero unplanned outages in 18 months. Every deployment goes through staged rollout."
        result = humanize(text)
        assert "testament to" not in result.lower()


# ---------------------------------------------------------------------------
# Throat Clearing
# ---------------------------------------------------------------------------

class TestThroatClearing:
    """Opening sentences that are meta-commentary about what follows."""

    def test_let_me_explain(self):
        text = "Let me explain how the authentication flow works. The client sends credentials to the auth server. The server returns a JWT with a 15-minute TTL."
        result = humanize(text)
        assert "let me explain" not in result.lower()
        assert "client sends credentials" in result

    def test_heres_a_breakdown(self):
        text = "Here's a breakdown of the deployment pipeline. Code merges trigger CI. Passing builds go to staging. Staging tests gate production deploys."
        result = humanize(text)
        assert "here's a breakdown" not in result.lower()

    def test_before_we_begin(self):
        text = "Before we begin, it's important to understand the prerequisites. You'll need Docker installed. The minimum version is 24.0. Port 8080 must be available."
        result = humanize(text)
        assert "before we begin" not in result.lower()


# ---------------------------------------------------------------------------
# should_humanize() gate
# ---------------------------------------------------------------------------

class TestShouldHumanize:
    """Tests for the gating function that decides whether to process text."""

    def test_short_text_skipped(self):
        from humanizer import should_humanize
        assert should_humanize("Quick answer: yes.") is False

    def test_code_block_skipped(self):
        from humanizer import should_humanize
        assert should_humanize("```python\nprint('hello')\n```\n" * 5) is False

    def test_json_skipped(self):
        from humanizer import should_humanize
        assert should_humanize('{"key": "value", "nested": {"a": 1}}') is False

    def test_long_prose_processed(self):
        from humanizer import should_humanize
        prose = "This is a test sentence that contains enough words. " * 20
        assert should_humanize(prose) is True

    def test_empty_string_skipped(self):
        from humanizer import should_humanize
        assert should_humanize("") is False


# ---------------------------------------------------------------------------
# Regression: patterns that kept coming back
# ---------------------------------------------------------------------------

class TestRegressions:
    """Patterns that were fixed but reappeared. Add new regressions here."""

    def test_regression_in_terms_of(self):
        """'In terms of' kept reappearing after being patched."""
        text = "In terms of performance, the new version is 3x faster. Memory usage dropped 40%. Startup time went from 8 seconds to under 2."
        result = humanize(text)
        assert "in terms of" not in result.lower()

    def test_regression_streamline(self):
        """'Streamline' kept appearing in process descriptions."""
        text = "The new tool streamlines the deployment process significantly. What used to take 6 steps now takes 2. Error rates dropped after the switch."
        result = humanize(text)
        assert "streamlines" not in result.lower()
        assert "simplifies" in result.lower()

    def test_regression_empower(self):
        text = "The platform empowers developers to ship faster by removing manual approval steps. PRs merge automatically after CI passes. Rollback is one click."
        result = humanize(text)
        assert "empowers" not in result.lower()

    def test_regression_elevate(self):
        text = "These changes will elevate the user experience across all platforms. Load times drop below 200ms. Error pages now show actionable recovery steps."
        result = humanize(text)
        assert "elevate" not in result.lower()

    def test_regression_harness(self):
        text = "Teams can harness the power of distributed computing without managing infrastructure. The platform handles scheduling. Auto-scaling responds to load in seconds."
        result = humanize(text)
        assert "harness the power" not in result.lower()

    def test_regression_double_em_dash(self):
        """Em dashes appearing in pairs for parenthetical asides."""
        text = "The system — which was built over three years — handles millions of requests daily. Each request is logged for audit purposes. Retention is 90 days."
        result = humanize(text)
        assert "—" not in result

    def test_regression_that_being_said(self):
        text = "That being said, the migration isn't without risks. Schema changes can break downstream consumers. We recommend a parallel-run period of at least two weeks."
        result = humanize(text)
        assert "that being said" not in result.lower()

    def test_regression_multifaceted(self):
        text = "Security is a multifaceted challenge that requires attention at every layer. Network isolation prevents lateral movement. Encryption protects data at rest and in transit."
        result = humanize(text)
        assert "multifaceted" not in result.lower()
        assert "complex" in result.lower()

    def test_preserves_content(self):
        """Humanizer should strip fluff but preserve all factual content."""
        text = ("It's worth noting that the API handles 50,000 requests per second. "
                "At the end of the day, latency stays under 10ms at p99. "
                "The system leverages Redis for session storage, "
                "showcasing the team's commitment to performance.")
        result = humanize(text)
        # All facts preserved
        assert "50,000 requests" in result
        assert "10ms" in result
        assert "Redis" in result
        # All fluff removed
        assert "worth noting" not in result.lower()
        assert "at the end of the day" not in result.lower()
        assert "leverages" not in result.lower()
        assert "showcasing" not in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
