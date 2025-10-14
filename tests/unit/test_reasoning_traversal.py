from services.langgraph.state import WorkflowState
from services.langgraph.workflow import (
    _order_mnemonics,
    _handle_well_relationship_queries,
)
from services.langgraph.aggregation import extract_field_from_query


class _StubTraverser:
    def __init__(self) -> None:
        self._well_id = 'force2020-well-123'
        common_file = 'sample.las'
        self._curves = {
            self._well_id: [
                {'id': 'curve-dept', 'attributes': {'mnemonic': 'DEPT', 'unit': 'm', 'source_file': common_file}},
                {'id': 'curve-depthmd', 'attributes': {'mnemonic': 'DEPTH_MD', 'unit': 'm', 'source_file': common_file}},
                {'id': 'curve-gr', 'attributes': {'mnemonic': 'GR', 'unit': 'api', 'source_file': common_file}},
                {'id': 'curve-nphi', 'attributes': {'mnemonic': 'NPHI', 'unit': '%', 'source_file': common_file}},
                {'id': 'curve-rhob', 'attributes': {'mnemonic': 'RHOB', 'unit': 'g/cm3', 'source_file': common_file}},
                {'id': 'curve-dtc', 'attributes': {'mnemonic': 'DTC', 'unit': 'us/ft', 'source_file': common_file}},
                {'id': 'curve-rdep', 'attributes': {'mnemonic': 'RDEP', 'unit': 'ohm.m', 'source_file': common_file}},
                {'id': 'curve-rmed', 'attributes': {'mnemonic': 'RMED', 'unit': 'ohm.m', 'source_file': common_file}},
                {'id': 'curve-rsha', 'attributes': {'mnemonic': 'RSHA', 'unit': 'ohm.m', 'source_file': common_file}},
                {'id': 'curve-rxo', 'attributes': {'mnemonic': 'RXO', 'unit': 'ohm.m', 'source_file': common_file}},
                {'id': 'curve-sp', 'attributes': {'mnemonic': 'SP', 'unit': 'mV', 'source_file': common_file}},
                {'id': 'curve-pef', 'attributes': {'mnemonic': 'PEF', 'unit': 'barns/e', 'source_file': common_file}},
                {'id': 'curve-lith', 'attributes': {'mnemonic': 'FORCE_2020_LITHOFACIES_LITHOLOGY', 'unit': '', 'source_file': common_file}},
                {'id': 'curve-lith-conf', 'attributes': {'mnemonic': 'FORCE_2020_LITHOFACIES_CONFIDENCE', 'unit': '', 'source_file': common_file}},
                {'id': 'curve-xloc', 'attributes': {'mnemonic': 'X_LOC', 'unit': 'm', 'source_file': 'survey.xyz'}},
                {'id': 'curve-yloc', 'attributes': {'mnemonic': 'Y_LOC', 'unit': 'm', 'source_file': 'survey.xyz'}},
                {'id': 'curve-zloc', 'attributes': {'mnemonic': 'Z_LOC', 'unit': 'm', 'source_file': 'survey.xyz'}},
            ]
        }
        self._well_node = {
            'id': self._well_id,
            'attributes': {
                'WELL': 'Sleipner East Appr',
                'UWI': '15/9-13'
            }
        }

    def get_curves_for_well(self, well_node_id):
        return list(self._curves.get(well_node_id, []))

    def get_wells_with_mnemonic(self, mnemonic):
        return [
            wid
            for wid, curves in self._curves.items()
            if any(str(c.get('attributes', {}).get('mnemonic', '')).upper() == mnemonic for c in curves)
        ]

    def get_node(self, node_id):
        if node_id == self._well_id:
            return self._well_node
        return None


def test_order_mnemonics_respects_primary_sequence():
    input_codes = ['unknown', 'gr', 'NPHI', 'DEPT', 'gr']
    ordered = _order_mnemonics(input_codes)
    assert ordered[:3] == ['DEPT', 'GR', 'NPHI']
    assert ordered[-1] == 'UNKNOWN'


def test_handle_well_relationship_curves_sets_structured_answer():
    state = WorkflowState(query='What curves belong to well 123?', metadata={'well_id_filter': '123'})
    traverser = _StubTraverser()

    assert _handle_well_relationship_queries(state, traverser, '123', state.query.lower())
    count = len(state.metadata['evidence_mnemonics'])
    assert state.response.startswith(f"{count} curves including:")
    assert 'force2020-well-123' in state.metadata['retrieved_node_ids']
    assert 'sample.las' in state.metadata['provenance_files']


def test_handle_well_relationship_classification_infers_basin():
    state = WorkflowState(query='What log suite classification does well 123 belong to?', metadata={'well_id_filter': '123'})
    traverser = _StubTraverser()

    assert _handle_well_relationship_queries(state, traverser, '123', state.query.lower())
    assert 'log suite classification' in state.response.lower()
    assert 'sleipner' in state.response.lower()
    assert 'north sea' in state.response.lower() or 'norwegian' in state.response.lower()
    assert state.metadata['relationship_structured_answer'] is True
    assert state.metadata.get('log_suite_summary')
    assert 'sample.las' in state.metadata['provenance_files']


def test_geological_setting_response_mentions_basin():
    state = WorkflowState(query='Describe the geological setting for well 123 based on logs', metadata={'well_id_filter': '123'})
    traverser = _StubTraverser()

    assert _handle_well_relationship_queries(state, traverser, '123', state.query.lower())
    assert 'geological setting' in state.response.lower()
    assert 'sleipner' in state.response.lower() or 'north sea' in state.response.lower()
    assert state.metadata['relationship_structured_answer'] is True
    assert 'geological_context' in state.metadata


def test_capability_matrix_includes_possible_and_impossible():
    state = WorkflowState(query='What interpretations are possible vs impossible in well 123?', metadata={'well_id_filter': '123'})
    traverser = _StubTraverser()

    assert _handle_well_relationship_queries(state, traverser, '123', state.query.lower())
    assert 'possible:' in state.response.lower()
    assert 'impossible:' in state.response.lower()
    matrix = state.metadata.get('capability_matrix')
    assert matrix and 'possible' in matrix and 'impossible' in matrix


def test_handle_well_relationship_counts_underscore_mnemonics():
    state = WorkflowState(query='Count how many curves in well 123 have underscore in their mnemonic', metadata={'well_id_filter': '123'})
    traverser = _StubTraverser()

    assert _handle_well_relationship_queries(state, traverser, '123', state.query.lower())
    assert state.response == '4'
    assert state.metadata['underscore_count'] == 4


def test_extract_field_from_query_prefers_matching_token():
    documents = [
        {'attributes': {'Oil (bbl/d)_Total production': 1000, 'region': 'Test Basin'}},
        {'attributes': {'Natural gas (Mcf/d)_Total production': 500}}
    ]
    field = extract_field_from_query('What is the total oil production for this dataset?', documents)
    assert field == 'Oil (bbl/d)_Total production'
