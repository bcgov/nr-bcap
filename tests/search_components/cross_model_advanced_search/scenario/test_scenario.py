from __future__ import annotations

from harness import Scenario, run
from shared import _uuid


def _assert_scenario(scenario: Scenario) -> None:
    result = run(scenario)
    assert result == scenario.expected, (
        f"[{scenario.name}] expected {len(scenario.expected)} IDs, "
        f"got {len(result)}: "
        f"missing={scenario.expected - result}, "
        f"extra={result - scenario.expected}"
    )


class TestDirectTranslation:
    def test_two_sources_to_two_targets(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1, a2 = _uuid(), _uuid()
        t1, t2, t3 = _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1, a2}},
            expected={t1, t2},
            graphs={graph_a: {a1, a2}, graph_t: {t1, t2, t3}},
            name="two_sources_to_two_targets",
            relationships={(a1, t1), (a2, t2)},
            target_graph=graph_t,
        ))

    def test_reverse_relationship_direction(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1, t1 = _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1}},
            expected={t1},
            graphs={graph_a: {a1}, graph_t: {t1}},
            name="reverse_relationship_direction",
            relationships={(t1, a1)},
            target_graph=graph_t,
        ))

    def test_bidirectional_no_double_count(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1, t1 = _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1}},
            expected={t1},
            graphs={graph_a: {a1}, graph_t: {t1}},
            name="bidirectional_no_double_count",
            relationships={(a1, t1), (t1, a1)},
            target_graph=graph_t,
        ))

    def test_one_to_many(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1 = _uuid()
        t1, t2, t3 = _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1}},
            expected={t1, t2, t3},
            graphs={graph_a: {a1}, graph_t: {t1, t2, t3}},
            name="one_to_many",
            relationships={(a1, t1), (a1, t2), (a1, t3)},
            target_graph=graph_t,
        ))

    def test_many_to_one(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1, a2, a3 = _uuid(), _uuid(), _uuid()
        t1 = _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1, a2, a3}},
            expected={t1},
            graphs={graph_a: {a1, a2, a3}, graph_t: {t1}},
            name="many_to_one",
            relationships={(a1, t1), (a2, t1), (a3, t1)},
            target_graph=graph_t,
        ))

    def test_partial_connectivity(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1, a2, a3 = _uuid(), _uuid(), _uuid()
        t1 = _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1, a2, a3}},
            expected={t1},
            graphs={graph_a: {a1, a2, a3}, graph_t: {t1}},
            name="partial_connectivity",
            relationships={(a1, t1)},
            target_graph=graph_t,
        ))

    def test_large_fan_out(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1 = _uuid()
        targets = {_uuid() for _ in range(50)}

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1}},
            expected=targets,
            graphs={graph_a: {a1}, graph_t: targets},
            name="large_fan_out",
            relationships={(a1, t) for t in targets},
            target_graph=graph_t,
        ))

    def test_large_fan_in(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        sources = {_uuid() for _ in range(50)}
        t1 = _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: sources},
            expected={t1},
            graphs={graph_a: sources, graph_t: {t1}},
            name="large_fan_in",
            relationships={(s, t1) for s in sources},
            target_graph=graph_t,
        ))


class TestSelfTranslation:
    def test_target_graph_filters_itself(self) -> None:
        graph_t = _uuid()
        t1, t2, t3 = _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            es_matches={graph_t: {t1, t2}},
            expected={t1, t2},
            graphs={graph_t: {t1, t2, t3}},
            name="target_graph_filters_itself",
            target_graph=graph_t,
        ))

    def test_minimal_single_resource(self) -> None:
        graph_t = _uuid()
        t1 = _uuid()

        _assert_scenario(Scenario(
            es_matches={graph_t: {t1}},
            expected={t1},
            graphs={graph_t: {t1}},
            name="minimal_single_resource",
            target_graph=graph_t,
        ))

    def test_all_resources_match(self) -> None:
        graph_t = _uuid()
        all_ids = {_uuid() for _ in range(10)}

        _assert_scenario(Scenario(
            es_matches={graph_t: all_ids},
            expected=all_ids,
            graphs={graph_t: all_ids},
            name="all_resources_match",
            target_graph=graph_t,
        ))


class TestMultiHopTranslation:
    def test_single_intermediate(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1 = _uuid()
        b1, b2 = _uuid(), _uuid()
        t1, t2 = _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_b],
                graph_b: [graph_a, graph_t],
                graph_t: [graph_b],
            },
            es_matches={graph_a: {a1}},
            expected={t1},
            graphs={
                graph_a: {a1},
                graph_b: {b1, b2},
                graph_t: {t1, t2},
            },
            name="single_intermediate",
            relationships={(a1, b1), (b1, t1)},
            target_graph=graph_t,
        ))

    def test_es_filter_narrows_intermediate(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1 = _uuid()
        b1, b2 = _uuid(), _uuid()
        t1, t2 = _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_b],
                graph_b: [graph_a, graph_t],
                graph_t: [graph_b],
            },
            es_matches={graph_a: {a1}, graph_b: {b1}},
            expected={t1},
            graphs={
                graph_a: {a1},
                graph_b: {b1, b2},
                graph_t: {t1, t2},
            },
            name="es_filter_narrows_intermediate",
            relationships={(a1, b1), (a1, b2), (b1, t1), (b2, t2)},
            target_graph=graph_t,
        ))

    def test_es_filter_eliminates_all_intermediates(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1 = _uuid()
        b1 = _uuid()
        t1 = _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_b],
                graph_b: [graph_a, graph_t],
                graph_t: [graph_b],
            },
            es_matches={graph_a: {a1}, graph_b: set()},
            expected=set(),
            graphs={
                graph_a: {a1},
                graph_b: {b1},
                graph_t: {t1},
            },
            name="es_filter_eliminates_all_intermediates",
            relationships={(a1, b1), (b1, t1)},
            target_graph=graph_t,
        ))

    def test_multiple_intermediates_first_empty_second_finds(self) -> None:
        graph_a, graph_b, graph_c, graph_t = _uuid(), _uuid(), _uuid(), _uuid()
        a1 = _uuid()
        b1, c1 = _uuid(), _uuid()
        t1 = _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_b, graph_c],
                graph_b: [graph_a, graph_t],
                graph_c: [graph_a, graph_t],
                graph_t: [graph_b, graph_c],
            },
            es_matches={graph_a: {a1}},
            expected={t1},
            graphs={
                graph_a: {a1},
                graph_b: {b1},
                graph_c: {c1},
                graph_t: {t1},
            },
            name="multiple_intermediates_first_empty_second_finds",
            relationships={(a1, c1), (c1, t1)},
            target_graph=graph_t,
        ))

    def test_unreachable_chain_beyond_two_hops(self) -> None:
        graph_a, graph_b, graph_c, graph_t = _uuid(), _uuid(), _uuid(), _uuid()
        a1, b1, c1, t1 = _uuid(), _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_b],
                graph_b: [graph_a, graph_c],
                graph_c: [graph_b, graph_t],
                graph_t: [graph_c],
            },
            es_matches={graph_a: {a1}},
            expected=set(),
            graphs={
                graph_a: {a1},
                graph_b: {b1},
                graph_c: {c1},
                graph_t: {t1},
            },
            name="unreachable_chain_beyond_two_hops",
            relationships={(a1, b1), (b1, c1), (c1, t1)},
            target_graph=graph_t,
        ))


class TestDiamondTopology:
    def test_two_paths_converge(self) -> None:
        graph_a, graph_b, graph_c, graph_t = _uuid(), _uuid(), _uuid(), _uuid()
        a1 = _uuid()
        b1, c1 = _uuid(), _uuid()
        t1 = _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_b, graph_c],
                graph_b: [graph_a, graph_t],
                graph_c: [graph_a, graph_t],
                graph_t: [graph_b, graph_c],
            },
            es_matches={graph_a: {a1}},
            expected={t1},
            graphs={
                graph_a: {a1},
                graph_b: {b1},
                graph_c: {c1},
                graph_t: {t1},
            },
            name="two_paths_converge",
            relationships={(a1, b1), (b1, t1), (a1, c1), (c1, t1)},
            target_graph=graph_t,
        ))

    def test_paths_reach_different_targets(self) -> None:
        graph_a, graph_b, graph_c, graph_t = _uuid(), _uuid(), _uuid(), _uuid()
        a1 = _uuid()
        b1, c1 = _uuid(), _uuid()
        t1, t2 = _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_b, graph_c],
                graph_b: [graph_a, graph_t],
                graph_c: [graph_a, graph_t],
                graph_t: [graph_b, graph_c],
            },
            es_matches={graph_a: {a1}},
            expected={t1, t2},
            graphs={
                graph_a: {a1},
                graph_b: {b1},
                graph_c: {c1},
                graph_t: {t1, t2},
            },
            name="paths_reach_different_targets",
            relationships={(a1, b1), (b1, t1), (a1, c1), (c1, t2)},
            target_graph=graph_t,
        ))


class TestIntersectOperation:
    def test_narrows_to_overlap(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1, a2 = _uuid(), _uuid()
        b1, b2 = _uuid(), _uuid()
        t1, t2, t3 = _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_t],
                graph_b: [graph_t],
                graph_t: [graph_a, graph_b],
            },
            es_matches={graph_a: {a1, a2}, graph_b: {b1, b2}},
            expected={t2},
            graphs={
                graph_a: {a1, a2},
                graph_b: {b1, b2},
                graph_t: {t1, t2, t3},
            },
            name="narrows_to_overlap",
            relationships={(a1, t1), (a2, t2), (b1, t2), (b2, t3)},
            target_graph=graph_t,
        ))

    def test_disjoint_translations_produce_empty(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1 = _uuid()
        b1 = _uuid()
        t1, t2 = _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_t],
                graph_b: [graph_t],
                graph_t: [graph_a, graph_b],
            },
            es_matches={graph_a: {a1}, graph_b: {b1}},
            expected=set(),
            graphs={
                graph_a: {a1},
                graph_b: {b1},
                graph_t: {t1, t2},
            },
            name="disjoint_translations_produce_empty",
            relationships={(a1, t1), (b1, t2)},
            target_graph=graph_t,
        ))

    def test_all_sources_translate_to_identical_set(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1 = _uuid()
        b1 = _uuid()
        t1, t2 = _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_t],
                graph_b: [graph_t],
                graph_t: [graph_a, graph_b],
            },
            es_matches={graph_a: {a1}, graph_b: {b1}},
            expected={t1, t2},
            graphs={
                graph_a: {a1},
                graph_b: {b1},
                graph_t: {t1, t2},
            },
            name="all_sources_translate_to_identical_set",
            relationships={(a1, t1), (a1, t2), (b1, t1), (b1, t2)},
            target_graph=graph_t,
        ))

    def test_three_sources_narrow_to_single_target(self) -> None:
        graph_a, graph_b, graph_c, graph_t = _uuid(), _uuid(), _uuid(), _uuid()
        a1, b1, c1 = _uuid(), _uuid(), _uuid()
        t1, t2, t3 = _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_t],
                graph_b: [graph_t],
                graph_c: [graph_t],
                graph_t: [graph_a, graph_b, graph_c],
            },
            es_matches={graph_a: {a1}, graph_b: {b1}, graph_c: {c1}},
            expected={t2},
            graphs={
                graph_a: {a1},
                graph_b: {b1},
                graph_c: {c1},
                graph_t: {t1, t2, t3},
            },
            name="three_sources_narrow_to_single_target",
            relationships={
                (a1, t1), (a1, t2),
                (b1, t2), (b1, t3),
                (c1, t2),
            },
            target_graph=graph_t,
        ))

    def test_empty_source_short_circuits(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1, t1 = _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1}, graph_b: set()},
            expected=set(),
            graphs={graph_a: {a1}, graph_b: set(), graph_t: {t1}},
            name="empty_source_short_circuits",
            relationships={(a1, t1)},
            target_graph=graph_t,
        ))

    def test_target_graph_empty_es_match_with_other_sources(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1 = _uuid()
        t1 = _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1}, graph_t: set()},
            expected=set(),
            graphs={graph_a: {a1}, graph_t: {t1}},
            name="target_graph_empty_es_match_with_other_sources",
            relationships={(a1, t1)},
            target_graph=graph_t,
        ))


class TestUnionOperation:
    def test_combines_all(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1, a2 = _uuid(), _uuid()
        b1, b2 = _uuid(), _uuid()
        t1, t2, t3 = _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_t],
                graph_b: [graph_t],
                graph_t: [graph_a, graph_b],
            },
            es_matches={graph_a: {a1, a2}, graph_b: {b1, b2}},
            expected={t1, t2, t3},
            graphs={
                graph_a: {a1, a2},
                graph_b: {b1, b2},
                graph_t: {t1, t2, t3},
            },
            name="combines_all",
            operation="union",
            relationships={(a1, t1), (a2, t2), (b1, t2), (b2, t3)},
            target_graph=graph_t,
        ))

    def test_ignores_empty_source(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1, t1 = _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1}, graph_b: set()},
            expected={t1},
            graphs={graph_a: {a1}, graph_b: set(), graph_t: {t1}},
            name="ignores_empty_source",
            operation="union",
            relationships={(a1, t1)},
            target_graph=graph_t,
        ))

    def test_deduplicates_overlapping_targets(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1, b1 = _uuid(), _uuid()
        t1 = _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_t],
                graph_b: [graph_t],
                graph_t: [graph_a, graph_b],
            },
            es_matches={graph_a: {a1}, graph_b: {b1}},
            expected={t1},
            graphs={graph_a: {a1}, graph_b: {b1}, graph_t: {t1}},
            name="deduplicates_overlapping_targets",
            operation="union",
            relationships={(a1, t1), (b1, t1)},
            target_graph=graph_t,
        ))

    def test_three_sources(self) -> None:
        graph_a, graph_b, graph_c, graph_t = _uuid(), _uuid(), _uuid(), _uuid()
        a1, b1, c1 = _uuid(), _uuid(), _uuid()
        t1, t2, t3 = _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_t],
                graph_b: [graph_t],
                graph_c: [graph_t],
                graph_t: [graph_a, graph_b, graph_c],
            },
            es_matches={graph_a: {a1}, graph_b: {b1}, graph_c: {c1}},
            expected={t1, t2, t3},
            graphs={
                graph_a: {a1},
                graph_b: {b1},
                graph_c: {c1},
                graph_t: {t1, t2, t3},
            },
            name="three_sources",
            operation="union",
            relationships={
                (a1, t1), (a1, t2),
                (b1, t2), (b1, t3),
                (c1, t2),
            },
            target_graph=graph_t,
        ))

    def test_five_sources_stress(self) -> None:
        graphs = [_uuid() for _ in range(5)]
        graph_t = _uuid()
        sources = {g: {_uuid()} for g in graphs}
        targets = {_uuid() for _ in range(5)}
        target_list = list(targets)

        rels = set()
        for i, g in enumerate(graphs):
            source_id = next(iter(sources[g]))
            rels.add((source_id, target_list[i % len(target_list)]))

        adjacency = {g: [graph_t] for g in graphs}
        adjacency[graph_t] = graphs

        all_graphs = dict(sources.items())
        all_graphs[graph_t] = targets

        _assert_scenario(Scenario(
            adjacency=adjacency,
            es_matches=dict(sources.items()),
            expected={target_list[i % len(target_list)] for i in range(len(graphs))},
            graphs=all_graphs,
            name="five_sources_stress",
            operation="union",
            relationships=rels,
            target_graph=graph_t,
        ))


class TestMixedSelfAndTranslated:
    def test_intersect_narrows_self_match(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1, a2 = _uuid(), _uuid()
        t1, t2, t3 = _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1, a2}, graph_t: {t1, t2}},
            expected={t2},
            graphs={graph_a: {a1, a2}, graph_t: {t1, t2, t3}},
            name="intersect_narrows_self_match",
            relationships={(a1, t2), (a2, t3)},
            target_graph=graph_t,
        ))

    def test_union_combines_self_and_translated(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1, a2 = _uuid(), _uuid()
        t1, t2, t3 = _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1, a2}, graph_t: {t1, t2}},
            expected={t1, t2, t3},
            graphs={graph_a: {a1, a2}, graph_t: {t1, t2, t3}},
            name="union_combines_self_and_translated",
            operation="union",
            relationships={(a1, t2), (a2, t3)},
            target_graph=graph_t,
        ))

    def test_intersect_self_match_is_superset(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1 = _uuid()
        t1, t2, t3 = _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1}, graph_t: {t1, t2, t3}},
            expected={t1},
            graphs={graph_a: {a1}, graph_t: {t1, t2, t3}},
            name="intersect_self_match_is_superset",
            relationships={(a1, t1)},
            target_graph=graph_t,
        ))


class TestDisconnectedAndEmpty:
    def test_no_relationships(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1, a2 = _uuid(), _uuid()
        t1 = _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1, a2}},
            expected=set(),
            graphs={graph_a: {a1, a2}, graph_t: {t1}},
            name="no_relationships",
            target_graph=graph_t,
        ))

    def test_empty_scenario(self) -> None:
        _assert_scenario(Scenario(
            expected=set(),
            name="empty_scenario",
            target_graph=_uuid(),
        ))

    def test_adjacency_exists_but_no_actual_links(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1 = _uuid()
        t1 = _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1}},
            expected=set(),
            graphs={graph_a: {a1}, graph_t: {t1}},
            name="adjacency_exists_but_no_actual_links",
            target_graph=graph_t,
        ))

    def test_direct_links_bypass_adjacency(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1, t1 = _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={},
            es_matches={graph_a: {a1}},
            expected={t1},
            graphs={graph_a: {a1}, graph_t: {t1}},
            name="direct_links_bypass_adjacency",
            relationships={(a1, t1)},
            target_graph=graph_t,
        ))

    def test_source_connected_to_non_target_resources_only(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1 = _uuid()
        b1 = _uuid()
        t1 = _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_b], graph_b: [graph_a]},
            es_matches={graph_a: {a1}},
            expected=set(),
            graphs={graph_a: {a1}, graph_b: {b1}, graph_t: {t1}},
            name="source_connected_to_non_target_resources_only",
            relationships={(a1, b1)},
            target_graph=graph_t,
        ))


class TestCyclicAdjacency:
    def test_two_graph_cycle(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1, t1 = _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={graph_a: [graph_t], graph_t: [graph_a]},
            es_matches={graph_a: {a1}},
            expected={t1},
            graphs={graph_a: {a1}, graph_t: {t1}},
            name="two_graph_cycle",
            relationships={(a1, t1)},
            target_graph=graph_t,
        ))

    def test_three_graph_cycle(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1, b1, t1 = _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_b, graph_t],
                graph_b: [graph_a, graph_t],
                graph_t: [graph_a, graph_b],
            },
            es_matches={graph_a: {a1}},
            expected={t1},
            graphs={graph_a: {a1}, graph_b: {b1}, graph_t: {t1}},
            name="three_graph_cycle",
            relationships={(a1, t1)},
            target_graph=graph_t,
        ))

    def test_cycle_with_no_path_to_target(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1, b1, t1 = _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={
                graph_a: [graph_b],
                graph_b: [graph_a],
            },
            es_matches={graph_a: {a1}},
            expected=set(),
            graphs={graph_a: {a1}, graph_b: {b1}, graph_t: {t1}},
            name="cycle_with_no_path_to_target",
            relationships={(a1, b1), (b1, a1)},
            target_graph=graph_t,
        ))


class TestFallbackConnected:
    def test_no_adjacency_falls_to_connected_then_intermediate(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1 = _uuid()
        b1 = _uuid()
        t1 = _uuid()

        _assert_scenario(Scenario(
            adjacency={},
            es_matches={graph_a: {a1}, graph_b: {b1}},
            expected={t1},
            graphs={graph_a: {a1}, graph_b: {b1}, graph_t: {t1}},
            name="no_adjacency_falls_to_connected_then_intermediate",
            relationships={(a1, b1), (b1, t1)},
            target_graph=graph_t,
        ))

    def test_fallback_connected_no_es_overlap(self) -> None:
        graph_a, graph_b, graph_t = _uuid(), _uuid(), _uuid()
        a1, b1, t1 = _uuid(), _uuid(), _uuid()

        _assert_scenario(Scenario(
            adjacency={},
            es_matches={graph_a: {a1}},
            expected=set(),
            graphs={graph_a: {a1}, graph_b: {b1}, graph_t: {t1}},
            name="fallback_connected_no_es_overlap",
            relationships={(a1, b1), (b1, t1)},
            target_graph=graph_t,
        ))

    def test_fallback_skips_source_and_target_graphs(self) -> None:
        graph_a, graph_t = _uuid(), _uuid()
        a1, t1 = _uuid(), _uuid()
        connected = _uuid()

        _assert_scenario(Scenario(
            adjacency={},
            es_matches={graph_a: {a1, connected}},
            expected=set(),
            graphs={graph_a: {a1, connected}, graph_t: {t1}},
            name="fallback_skips_source_and_target_graphs",
            relationships={(a1, connected)},
            target_graph=graph_t,
        ))
