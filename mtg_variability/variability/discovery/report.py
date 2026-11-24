
"""Markdown report generation for variability discovery."""

from __future__ import annotations

from mtg_variability.variability.discovery.inspector import (
    AttributeInspection,
    DatasetInspection,
)


class InspectionReport:
    """Generates human-readable reports from dataset inspections."""

    def __init__(self, max_values: int = 5) -> None:
        if max_values < 0:
            raise ValueError("Maximum number of values cannot be negative.")

        self.max_values = max_values

    def render(self, inspection: DatasetInspection) -> str:
        """Generates a Markdown report for a dataset inspection.

        Args:
            inspection: Results produced by DatasetInspector.

        Returns:
            A Markdown document containing the inspection results.
        """
        sections = [
            self._render_summary(inspection),
            self._render_attribute_overview(inspection),
            self._render_candidates(inspection),
            self._render_review_attributes(inspection),
        ]

        return "\n\n".join(sections) + "\n"

    def _render_summary(self, inspection: DatasetInspection) -> str:
        """Renders the dataset summary."""
        candidate_count = len(inspection.candidates)
        review_count = len(inspection.attributes_requiring_review)

        return "\n".join(
            [
                "# Variability Inspection Report",
                "",
                "## Dataset Summary",
                "",
                f"- **Total records:** {inspection.total_records}",
                f"- **Total attributes:** {inspection.attribute_count}",
                f"- **Variability candidates:** {candidate_count}",
                f"- **Attributes requiring review:** {review_count}",
            ]
        )

    def _render_attribute_overview(
        self,
        inspection: DatasetInspection,
    ) -> str:
        """Renders a table with all inspected attributes."""
        lines = [
            "## Attribute Overview",
            "",
            "| Attribute | Classification | Distinct values | Missing | Missing ratio |",
            "|---|---|---:|---:|---:|",
        ]

        if not inspection.attributes:
            lines.append("| — | — | — | — | — |")
            return "\n".join(lines)

        for attribute in inspection.attributes.values():
            profile = attribute.profile

            lines.append(
                f"| {self._escape(attribute.name)} "
                f"| {attribute.classification.value} "
                f"| {profile.distinct_count} "
                f"| {profile.missing_count} "
                f"| {profile.missing_ratio:.2%} |"
            )

        return "\n".join(lines)

    def _render_candidates(
        self,
        inspection: DatasetInspection,
    ) -> str:
        """Renders the attributes identified as candidates."""
        lines = [
            "## Variability Candidates",
            "",
        ]

        candidates = inspection.candidates

        if not candidates:
            lines.append("No variability candidates were identified.")
            return "\n".join(lines)

        for attribute in candidates:
            lines.extend(self._render_attribute_details(attribute))

        return "\n".join(lines)

    def _render_review_attributes(
        self,
        inspection: DatasetInspection,
    ) -> str:
        """Renders attributes that require further inspection."""
        lines = [
            "## Attributes Requiring Review",
            "",
        ]

        attributes = inspection.attributes_requiring_review

        if not attributes:
            lines.append("No attributes require further review.")
            return "\n".join(lines)

        for attribute in attributes:
            lines.extend(self._render_attribute_details(attribute))

        return "\n".join(lines)

    def _render_attribute_details(
        self,
        attribute: AttributeInspection,
    ) -> list[str]:
        """Renders detailed information about an attribute."""
        profile = attribute.profile

        lines = [
            f"### {self._escape(attribute.name)}",
            "",
            f"- **Classification:** {attribute.classification.value}",
            f"- **Distinct values:** {profile.distinct_count}",
            f"- **Observed values:** {profile.non_missing_count}",
            f"- **Missing values:** {profile.missing_count}",
            f"- **Missing ratio:** {profile.missing_ratio:.2%}",
        ]

        if attribute.reasons:
            lines.append(
                f"- **Reason:** {' '.join(attribute.reasons)}"
            )

        lines.extend(
            [
                "",
                "**Most frequent values:**",
                "",
            ]
        )

        values = profile.most_common(self.max_values)

        if not values:
            lines.append("No observed values.")
        else:
            for value, count in values:
                ratio = count / profile.non_missing_count
                lines.append(
                    f"- `{self._escape_code(value)}`: "
                    f"{count} ({ratio:.2%})"
                )

            if profile.distinct_count > len(values):
                remaining = profile.distinct_count - len(values)
                lines.append(
                    f"- *...and {remaining} additional distinct values.*"
                )

        lines.append("")

        return lines

    @staticmethod
    def _escape(value: str) -> str:
        """Escapes characters that have special meaning in Markdown tables."""
        return (
            value.replace("\\", "\\\\")
            .replace("|", "\\|")
            .replace("\n", " ")
            .replace("\r", " ")
        )

    @staticmethod
    def _escape_code(value: str) -> str:
        """Escapes backticks in inline code spans."""
        return value.replace("`", "\\`")
