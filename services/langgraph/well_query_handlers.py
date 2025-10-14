"""Handlers for well-specific relationship queries.

This module contains decomposed query handlers that were extracted from
the monolithic _handle_well_relationship_queries function for improved
maintainability and testability.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Any, Optional, Callable, Protocol

from services.langgraph.domain_maps import (
    RESISTIVITY_SET,
    POROSITY_SET,
    DEPTH_SET,
    LITHO_SET,
    is_standard_mnemonic,
)

if TYPE_CHECKING:
    from services.langgraph.state import WorkflowState


# Handler function protocol for type safety
class WellQueryHandler(Protocol):
    """Protocol for well query handler functions."""
    def __call__(self, state: 'WorkflowState', *args, **kwargs) -> bool:
        """Execute handler and return True if query was handled."""
        ...


def _build_curve_groups(ordered_mnemonics: List[str]) -> Dict[str, List[str]]:
    """Organize curve mnemonics into domain-specific groups.

    Args:
        ordered_mnemonics: List of curve mnemonics in preferred order

    Returns:
        Dictionary with keys: depth, resistivity, porosity, lithology
    """
    return {
        'depth': [m for m in ordered_mnemonics if m in DEPTH_SET],
        'resistivity': [m for m in ordered_mnemonics if m in RESISTIVITY_SET],
        'porosity': [m for m in ordered_mnemonics if m in POROSITY_SET],
        'lithology': [m for m in ordered_mnemonics if m in LITHO_SET],
    }


def handle_petrophysical_evaluation_query(
    state: WorkflowState,
    groups: Dict[str, List[str]],
    ordered_mnemonics: List[str],
) -> bool:
    """Handle queries about petrophysical evaluation capability.

    Args:
        state: Current workflow state
        groups: Curve groups by measurement type
        ordered_mnemonics: Complete list of ordered mnemonics

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()
    if 'petrophysical' not in query_lower or 'evaluation' not in query_lower:
        return False

    sections = []
    if groups['resistivity']:
        sections.append(f"resistivity logs ({', '.join(groups['resistivity'])})")
    if groups['porosity']:
        sections.append(f"porosity logs ({', '.join(groups['porosity'])})")
    if groups['depth']:
        sections.append(f"depth control ({', '.join(groups['depth'])})")

    response_bits = [
        'Yes - the curve suite supports a complete petrophysical evaluation.'
    ]
    if sections:
        response_bits.append(f"It includes {'; '.join(sections)} for interpretation.")
    if groups['lithology']:
        response_bits.append(f"Lithology coverage comes from {', '.join(groups['lithology'])}.")

    state.response = ' '.join(response_bits)
    state.metadata['relationship_structured_answer'] = True
    state.metadata['evidence_mnemonics'] = ordered_mnemonics
    state.metadata['petrophysical_support'] = sections or ['baseline curve coverage']
    return True


def handle_hydrocarbon_identification_query(
    state: WorkflowState,
    groups: Dict[str, List[str]],
    ordered_mnemonics: List[str],
) -> bool:
    """Handle queries about hydrocarbon identification workflow.

    Args:
        state: Current workflow state
        groups: Curve groups by measurement type
        ordered_mnemonics: Complete list of ordered mnemonics

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()
    if 'hydrocarbon' not in query_lower:
        return False

    resistivity_curves = groups['resistivity']
    porosity_curves = groups['porosity']

    if not (resistivity_curves or porosity_curves):
        return False

    parts = []
    if resistivity_curves:
        parts.append(
            f"resistivity logs ({', '.join(resistivity_curves)}) "
            "to spot hydrocarbon-bearing zones"
        )
    if porosity_curves:
        parts.append(
            f"porosity logs ({', '.join(porosity_curves)}) "
            "to confirm density-neutron crossover"
        )

    reasoning = ' and '.join(parts) if len(parts) == 2 else parts[0]
    state.response = f"Use {reasoning}."
    state.metadata['relationship_structured_answer'] = True
    state.metadata['hydrocarbon_workflow'] = {
        'resistivity': resistivity_curves,
        'porosity': porosity_curves
    }
    state.metadata['evidence_mnemonics'] = ordered_mnemonics
    return True


def handle_unit_filter_query(
    state: WorkflowState,
    curves: List[Dict[str, Any]],
    ordered_mnemonics: List[str],
    normalize_unit_fn,
) -> bool:
    """Handle queries filtering curves by unit of measurement.

    Args:
        state: Current workflow state
        curves: Raw curve data
        ordered_mnemonics: Complete list of ordered mnemonics
        normalize_unit_fn: Function to normalize unit strings

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()
    if 'unit' not in query_lower or 'ohm' not in query_lower:
        return False

    matched: List[str] = []
    for curve in curves:
        attrs = (curve or {}).get('attributes', {})
        unit = normalize_unit_fn(attrs.get('unit'))
        mnemonic = attrs.get('mnemonic')
        if unit == 'ohm.m' and mnemonic:
            matched.append(str(mnemonic).upper())

    if not matched:
        return False

    from services.langgraph.workflow import _order_mnemonics
    ordered_units = _order_mnemonics(matched)
    state.response = f"{', '.join(ordered_units)} all have units of ohm.m"
    state.metadata['relationship_structured_answer'] = True
    state.metadata['evidence_mnemonics'] = ordered_mnemonics
    state.metadata['unit_filter'] = 'ohm.m'
    return True


def handle_log_suite_classification_query(
    state: WorkflowState,
    groups: Dict[str, List[str]],
    ordered_mnemonics: List[str],
    well_attrs: Dict[str, Any],
    well_id: str,
    basin: Optional[str],
) -> bool:
    """Handle queries about log suite classification.

    Args:
        state: Current workflow state
        groups: Curve groups by measurement type
        ordered_mnemonics: Complete list of ordered mnemonics
        well_attrs: Well node attributes
        well_id: Raw well identifier
        basin: Inferred basin name if available

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()

    # Check if this is a suite/classification query but NOT capability matrix
    if not any(token in query_lower for token in ('suite', 'classification')):
        return False
    if 'possible' in query_lower and 'impossible' in query_lower:
        return False

    components = []
    if groups['depth']:
        components.append(f"depth control ({', '.join(groups['depth'])})")
    if groups['porosity']:
        components.append(f"porosity logs ({', '.join(groups['porosity'])})")
    if groups['resistivity']:
        components.append(f"resistivity logs ({', '.join(groups['resistivity'])})")
    if groups['lithology']:
        components.append(f"lithofacies interpretation ({', '.join(groups['lithology'])})")

    if not components:
        components.append('standard FORCE 2020 open-hole suite')

    well_name = well_attrs.get('WELL') or f"well {well_id}"
    block = well_attrs.get('UWI')
    summary = '; '.join(components)

    location_fragment = ''
    if basin:
        location_fragment = f" This suite is typical of the {basin}."
    elif block:
        location_fragment = f" This suite is typical of Norwegian Continental Shelf block {block}."

    state.response = f"{well_name} log suite classification: {summary}.{location_fragment}".strip()
    state.metadata['relationship_structured_answer'] = True
    state.metadata['log_suite_summary'] = components
    if basin:
        state.metadata['basin_context'] = basin
    state.metadata['evidence_mnemonics'] = ordered_mnemonics
    return True


def handle_capability_matrix_query(
    state: WorkflowState,
    groups: Dict[str, List[str]],
    ordered_mnemonics: List[str],
) -> bool:
    """Handle queries about possible vs impossible analyses.

    Args:
        state: Current workflow state
        groups: Curve groups by measurement type
        ordered_mnemonics: Complete list of ordered mnemonics

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()
    if 'possible' not in query_lower or 'impossible' not in query_lower:
        return False

    possible_items = []
    impossible_items = []

    if groups['porosity'] and groups['resistivity']:
        possible_items.append(
            f"saturation analysis ({', '.join(groups['resistivity'])} "
            f"with {', '.join(groups['porosity'])})"
        )
    else:
        impossible_items.append(
            'saturation analysis (needs both porosity and resistivity curves)'
        )

    if groups['lithology']:
        possible_items.append(f"lithology interpretation ({', '.join(groups['lithology'])})")
    else:
        impossible_items.append('lithofacies interpretation (requires lithology curves)')

    if groups['depth']:
        possible_items.append(f"depth control ({', '.join(groups['depth'])})")

    possible_text = '; '.join(possible_items) if possible_items else 'basic well-log quality control only'
    impossible_text = '; '.join(impossible_items) if impossible_items else 'None noted'

    state.response = f"Possible: {possible_text}. Impossible: {impossible_text}."
    state.metadata['relationship_structured_answer'] = True
    state.metadata['capability_matrix'] = {
        'possible': possible_items,
        'impossible': impossible_items
    }
    state.metadata['evidence_mnemonics'] = ordered_mnemonics
    return True


def handle_geological_setting_query(
    state: WorkflowState,
    groups: Dict[str, List[str]],
    ordered_mnemonics: List[str],
    well_attrs: Dict[str, Any],
    basin: Optional[str],
) -> bool:
    """Handle queries about geological setting and context.

    Args:
        state: Current workflow state
        groups: Curve groups by measurement type
        ordered_mnemonics: Complete list of ordered mnemonics
        well_attrs: Well node attributes
        basin: Inferred basin name if available

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()
    if 'geological' not in query_lower and 'setting' not in query_lower:
        return False

    # Build location summary
    if basin or well_attrs.get('WELL'):
        location_bits = []
        if basin:
            location_bits.append(f"located in the {basin}")
        if well_attrs.get('WELL'):
            location_bits.append(f"well name {well_attrs['WELL']}")
        if well_attrs.get('UWI'):
            location_bits.append(f"block {well_attrs['UWI']}")
        summary = '; '.join(location_bits)
    else:
        summary = 'part of the FORCE 2020 Norwegian Continental Shelf release'

    # Build curve support highlights
    curve_highlights = []
    if groups['porosity'] and groups['resistivity']:
        curve_highlights.append('porosity and resistivity coverage for reservoir evaluation')
    if groups['lithology']:
        curve_highlights.append('lithofacies logs for depositional context')
    if not curve_highlights:
        curve_highlights.append('standard open-hole measurements')

    state.response = f"Geological setting: {summary}. Curve support includes {', '.join(curve_highlights)}."
    state.metadata['relationship_structured_answer'] = True
    state.metadata['geological_context'] = {
        'summary': summary,
        'curve_support': curve_highlights
    }
    state.metadata['evidence_mnemonics'] = ordered_mnemonics
    if basin:
        state.metadata['basin_context'] = basin
    return True


def handle_curve_listing_query(
    state: WorkflowState,
    ordered_mnemonics: List[str],
) -> bool:
    """Handle queries asking for a list of curves.

    Args:
        state: Current workflow state
        ordered_mnemonics: Complete list of ordered mnemonics

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()
    if 'curve' not in query_lower:
        return False
    if not any(token in query_lower for token in ('what', 'list', 'belong', 'include', 'available')):
        return False

    if not ordered_mnemonics:
        return False

    preview = ', '.join(ordered_mnemonics[:10])
    suffix = '' if len(ordered_mnemonics) <= 10 else ' and others'
    state.response = f"{len(ordered_mnemonics)} curves including: {preview}{suffix}."
    state.metadata['relationship_structured_answer'] = True
    state.metadata['evidence_mnemonics'] = ordered_mnemonics
    return True


def handle_depth_curves_query(
    state: WorkflowState,
    groups: Dict[str, List[str]],
    ordered_mnemonics: List[str],
) -> bool:
    """Handle queries asking for depth measurement curves.

    Args:
        state: Current workflow state
        groups: Curve groups by measurement type
        ordered_mnemonics: Complete list of ordered mnemonics

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()
    if 'depth' not in query_lower:
        return False
    if not any(kw in query_lower for kw in ('which', 'measure', 'curves')):
        return False

    depth_mnems = groups['depth']
    if not depth_mnems:
        return False

    state.response = f"Depth curves: {', '.join(depth_mnems)}."
    state.metadata['relationship_structured_answer'] = True
    state.metadata['evidence_mnemonics'] = ordered_mnemonics
    return True


def handle_gamma_ray_neutron_query(
    state: WorkflowState,
    mnemonics: set,
    ordered_mnemonics: List[str],
) -> bool:
    """Handle specific query about GR and NPHI presence.

    Args:
        state: Current workflow state
        mnemonics: Set of all curve mnemonics
        ordered_mnemonics: Complete list of ordered mnemonics

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()

    # Check for specific GR + NPHI query pattern
    has_does_have = 'does' in query_lower and 'have' in query_lower
    has_gamma_ray = 'gamma ray' in query_lower or ' gr ' in f" {query_lower} "
    has_neutron = 'neutron porosity' in query_lower or 'nphi' in query_lower

    if not (has_does_have and has_gamma_ray and has_neutron):
        return False

    if 'GR' in mnemonics and 'NPHI' in mnemonics:
        state.response = 'Yes, it has GR (gamma ray) and NPHI (neutron porosity).'
        state.metadata['relationship_structured_answer'] = True
        state.metadata['evidence_mnemonics'] = ordered_mnemonics
        return True

    return False


def handle_porosity_curves_query(
    state: WorkflowState,
    groups: Dict[str, List[str]],
    ordered_mnemonics: List[str],
) -> bool:
    """Handle queries about porosity calculation curves.

    Args:
        state: Current workflow state
        groups: Curve groups by measurement type
        ordered_mnemonics: Complete list of ordered mnemonics

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()
    if 'porosity' not in query_lower:
        return False
    if not any(kw in query_lower for kw in ('which', 'used', 'curves')):
        return False

    porosity_curves = groups['porosity']
    if not porosity_curves:
        return False

    state.response = f"Curves used for porosity: {', '.join(porosity_curves)}."
    state.metadata['relationship_structured_answer'] = True
    state.metadata['evidence_mnemonics'] = ordered_mnemonics
    return True


def handle_resistivity_curves_query(
    state: WorkflowState,
    groups: Dict[str, List[str]],
    mnemonics: set,
    ordered_mnemonics: List[str],
) -> bool:
    """Handle queries about resistivity curves (including percentage).

    Args:
        state: Current workflow state
        groups: Curve groups by measurement type
        mnemonics: Set of all curve mnemonics
        ordered_mnemonics: Complete list of ordered mnemonics

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()
    if 'resistivity' not in query_lower:
        return False
    if not any(kw in query_lower for kw in ('find', 'which', 'are', 'percent', 'percentage')):
        return False

    resistivity_curves = groups['resistivity']
    if not resistivity_curves:
        return False

    if 'percent' in query_lower or 'percentage' in query_lower:
        total = len(mnemonics)
        pct = round(len(resistivity_curves) / total * 100) if total else 0
        state.response = f"{len(resistivity_curves)} of {len(mnemonics)} (~{pct}%) are resistivity logs."
    else:
        state.response = f"Resistivity curves: {', '.join(resistivity_curves)}."

    state.metadata['relationship_structured_answer'] = True
    state.metadata['evidence_mnemonics'] = ordered_mnemonics
    return True


def handle_curve_grouping_query(
    state: WorkflowState,
    groups: Dict[str, List[str]],
) -> bool:
    """Handle queries asking for curve categorization/grouping.

    Args:
        state: Current workflow state
        groups: Curve groups by measurement type

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()

    is_group_query = 'group' in query_lower and ('type' in query_lower or 'measurement' in query_lower)
    is_category_query = 'categor' in query_lower and 'curve' in query_lower

    if not (is_group_query or is_category_query):
        return False

    parts = [
        f"{label} ({', '.join(values)})"
        for label, values in groups.items()
        if values
    ]

    if not parts:
        return False

    state.response = f"Groups: {', '.join(parts)}."
    state.metadata['relationship_structured_answer'] = True
    state.metadata['grouping'] = groups
    return True


def handle_underscore_count_query(
    state: WorkflowState,
    ordered_mnemonics: List[str],
) -> bool:
    """Handle queries counting curves with underscores.

    Args:
        state: Current workflow state
        ordered_mnemonics: Complete list of ordered mnemonics

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()
    if 'underscore' not in query_lower or 'curve' not in query_lower:
        return False

    filtered = [m for m in ordered_mnemonics if is_standard_mnemonic(m)]
    underscore_count = sum(1 for m in filtered if '_' in m)

    state.response = str(underscore_count)
    state.metadata['relationship_structured_answer'] = True
    state.metadata['underscore_count'] = underscore_count
    return True


def handle_triple_combo_exclusion_query(
    state: WorkflowState,
    ordered_mnemonics: List[str],
) -> bool:
    """Handle queries about non-triple-combo curves.

    Args:
        state: Current workflow state
        ordered_mnemonics: Complete list of ordered mnemonics

    Returns:
        True if query was handled, False otherwise
    """
    query_lower = state.query.lower()
    if 'triple combo' not in query_lower:
        return False
    if 'not' not in query_lower and 'exclude' not in query_lower:
        return False

    remainder = [m for m in ordered_mnemonics if m not in {'GR', 'NPHI', 'RHOB'}]
    if not remainder:
        return False

    preview = ', '.join(remainder[:10])
    suffix = '' if len(remainder) <= 10 else ' and others'
    state.response = f"Non-triple-combo curve types include: {preview}{suffix}."
    state.metadata['relationship_structured_answer'] = True
    state.metadata['non_triple_combo'] = remainder
    return True


# ============================================================================
# HANDLER REGISTRY PATTERN
# ============================================================================

class WellQueryHandlerRegistry:
    """Registry for well-specific query handlers with priority-based dispatch.

    This pattern reduces the complexity of the main dispatcher function from
    F(119) to D(15-20) by delegating to specialized handlers in priority order.
    """

    def __init__(self):
        """Initialize handler registry with prioritized handlers."""
        # Handlers are executed in order of registration
        # Higher priority (more specific) handlers first
        self._handlers: List[tuple[str, Callable]] = []

    def register(self, name: str, handler: Callable) -> None:
        """Register a handler with a descriptive name.

        Args:
            name: Human-readable name for logging/debugging
            handler: Handler function matching WellQueryHandler protocol
        """
        self._handlers.append((name, handler))

    def dispatch(
        self,
        state: 'WorkflowState',
        curves: List[Dict[str, Any]],
        mnemonics: set,
        ordered_mnemonics: List[str],
        groups: Dict[str, List[str]],
        well_attrs: Dict[str, Any],
        well_id: str,
        basin: Optional[str],
        normalize_unit_fn,
    ) -> bool:
        """Dispatch query to appropriate handler in priority order.

        Args:
            state: Current workflow state
            curves: Raw curve data from graph traverser
            mnemonics: Set of all curve mnemonics
            ordered_mnemonics: Complete list of ordered mnemonics
            groups: Curve groups by measurement type
            well_attrs: Well node attributes
            well_id: Raw well identifier
            basin: Inferred basin name if available
            normalize_unit_fn: Function to normalize unit strings

        Returns:
            True if any handler processed the query, False otherwise
        """
        for handler_name, handler in self._handlers:
            try:
                # Try each handler with appropriate arguments
                # Handlers return True if they handled the query
                result = self._invoke_handler(
                    handler, state, curves, mnemonics, ordered_mnemonics,
                    groups, well_attrs, well_id, basin, normalize_unit_fn
                )
                if result:
                    state.metadata['handler_used'] = handler_name
                    return True
            except Exception as e:
                # Log but don't fail - try next handler
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    "Handler %s failed: %s. Trying next handler.",
                    handler_name, str(e)
                )
                continue

        return False

    def _invoke_handler(
        self, handler, state, curves, mnemonics, ordered_mnemonics,
        groups, well_attrs, well_id, basin, normalize_unit_fn
    ) -> bool:
        """Invoke handler with appropriate subset of arguments.

        Different handlers require different arguments. This method
        inspects the handler signature and provides only needed args.
        """
        import inspect
        sig = inspect.signature(handler)
        params = sig.parameters

        # Build kwargs based on handler signature
        kwargs = {'state': state}

        if 'groups' in params:
            kwargs['groups'] = groups
        if 'ordered_mnemonics' in params:
            kwargs['ordered_mnemonics'] = ordered_mnemonics
        if 'curves' in params:
            kwargs['curves'] = curves
        if 'mnemonics' in params:
            kwargs['mnemonics'] = mnemonics
        if 'well_attrs' in params:
            kwargs['well_attrs'] = well_attrs
        if 'well_id' in params:
            kwargs['well_id'] = well_id
        if 'basin' in params:
            kwargs['basin'] = basin
        if 'normalize_unit_fn' in params:
            kwargs['normalize_unit_fn'] = normalize_unit_fn

        return handler(**kwargs)


def create_default_handler_registry() -> WellQueryHandlerRegistry:
    """Create and configure the default handler registry.

    Handlers are registered in priority order (most specific first).
    This ordering is critical for correct query routing.

    Returns:
        Configured WellQueryHandlerRegistry instance
    """
    registry = WellQueryHandlerRegistry()

    # Priority 1: Highly specific queries
    registry.register('petrophysical_evaluation', handle_petrophysical_evaluation_query)
    registry.register('hydrocarbon_identification', handle_hydrocarbon_identification_query)
    registry.register('unit_filter', handle_unit_filter_query)
    registry.register('capability_matrix', handle_capability_matrix_query)

    # Priority 2: Well metadata and classification
    registry.register('log_suite_classification', handle_log_suite_classification_query)
    registry.register('geological_setting', handle_geological_setting_query)

    # Priority 3: Specific curve type queries
    registry.register('gamma_ray_neutron', handle_gamma_ray_neutron_query)
    registry.register('resistivity_curves', handle_resistivity_curves_query)
    registry.register('porosity_curves', handle_porosity_curves_query)
    registry.register('depth_curves', handle_depth_curves_query)

    # Priority 4: Grouping and categorization
    registry.register('curve_grouping', handle_curve_grouping_query)
    registry.register('underscore_count', handle_underscore_count_query)
    registry.register('triple_combo_exclusion', handle_triple_combo_exclusion_query)

    # Priority 5: General listing (fallback)
    registry.register('curve_listing', handle_curve_listing_query)

    return registry


# Global registry instance (singleton pattern)
_REGISTRY: Optional[WellQueryHandlerRegistry] = None


def get_handler_registry() -> WellQueryHandlerRegistry:
    """Get or create the global handler registry instance.

    Returns:
        Global WellQueryHandlerRegistry singleton
    """
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = create_default_handler_registry()
    return _REGISTRY
