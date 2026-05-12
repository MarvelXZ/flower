"""Rule model and operator engine.

A ``Rule`` defines a named condition: ``metric_key`` compared to
``threshold_value`` using ``operator``.  When the condition is met,
an alert of the rule's ``severity`` is opened — subject to
``cooldown_seconds`` deduplication.

Operators are centrally defined and validated — new operators must
be added to ``ALLOWED_OPERATORS``.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

# ---------------------------------------------------------------------------
# Operator registry — central definition
# ---------------------------------------------------------------------------

class RuleOperator(models.TextChoices):
    GT = "gt", _("Greater than")
    GTE = "gte", _("Greater than or equal")
    LT = "lt", _("Less than")
    LTE = "lte", _("Less than or equal")
    EQ = "eq", _("Equal")
    NEQ = "neq", _("Not equal")


# Operator functions: each takes (value, threshold) and returns bool.
_OPERATOR_FUNCTIONS = {
    RuleOperator.GT: lambda v, t: v > t,
    RuleOperator.GTE: lambda v, t: v >= t,
    RuleOperator.LT: lambda v, t: v < t,
    RuleOperator.LTE: lambda v, t: v <= t,
    RuleOperator.EQ: lambda v, t: v == t,
    RuleOperator.NEQ: lambda v, t: v != t,
}


def evaluate_operator(*, value: float, operator: str, threshold: float) -> bool:
    """Evaluate a value against a threshold using the given operator.

    Raises ``ValueError`` if the operator is unknown.
    """
    fn = _OPERATOR_FUNCTIONS.get(operator)
    if fn is None:
        raise ValueError(
            f"Unknown operator '{operator}'. "
            f"Allowed: {sorted(_OPERATOR_FUNCTIONS.keys())}"
        )
    return fn(value, threshold)


# ---------------------------------------------------------------------------
# Rule model
# ---------------------------------------------------------------------------


class Rule(models.Model):
    """A configurable rule that triggers alerts when a condition is met.

    Rules are tenant-aware (live in the tenant schema).  Each rule
    monitors a specific ``metric_key`` and opens an alert when the
    condition is satisfied.  ``cooldown_seconds`` prevents alert spam
    by suppressing repeated triggers within the cooldown window.
    """

    class Severity(models.TextChoices):
        INFO = "info", _("Info")
        WARNING = "warning", _("Warning")
        CRITICAL = "critical", _("Critical")

    name = models.CharField(max_length=180, verbose_name=_("name"))
    description = models.TextField(blank=True, default="", verbose_name=_("description"))
    metric_key = models.CharField(
        max_length=120,
        verbose_name=_("metric key"),
        help_text=_("The metric this rule evaluates (e.g. soil_moisture, temperature)."),
    )
    operator = models.CharField(
        max_length=10,
        choices=RuleOperator.choices,
        verbose_name=_("operator"),
    )
    threshold_value = models.FloatField(verbose_name=_("threshold value"))
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.WARNING,
        verbose_name=_("severity"),
    )
    enabled = models.BooleanField(default=True, verbose_name=_("enabled"))
    cooldown_seconds = models.PositiveIntegerField(
        default=300,
        verbose_name=_("cooldown (seconds)"),
        help_text=_("Minimum interval between alert triggers. 0 = no cooldown."),
    )
    metadata = models.JSONField(
        default=dict, blank=True, verbose_name=_("metadata"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("rule")
        verbose_name_plural = _("rules")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["metric_key", "enabled"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.metric_key} {self.operator} {self.threshold_value})"

    def evaluate(self, value: float) -> bool:
        """Return True if the value triggers this rule."""
        if not self.enabled:
            return False
        return evaluate_operator(
            value=value,
            operator=self.operator,
            threshold=self.threshold_value,
        )

    def alert_key(self, *, device_identifier: str) -> str:
        """Build a deterministic alert dedup key for this rule + device."""
        return f"rule:{self.pk}:{self.metric_key}:device:{device_identifier}"
