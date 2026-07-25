drop function if exists get_map_attribute_data;
create or replace function get_map_attribute_data(p_resourceinstanceid uuid, nodeid uuid) returns jsonb as
    $$
declare
    data jsonb;
begin
    if nodeid = archaeological_site.node_alias_uuid('site_boundary') then -- Archaeological Site
        with borden_number as (
            select resourceinstanceid,
                   tiledata ->> archaeological_site.node_alias_uuid('borden_number')::text as borden_number
            from tiles
            where nodegroupid = archaeological_site.node_alias_uuid('identification_and_registration')
              and resourceinstanceid = p_resourceinstanceid
        ),
        arch_site_leg_acts as (
            select t.resourceinstanceid,
                   (jsonb_array_elements(tiledata -> archaeological_site.node_alias_uuid('legislative_act')::text) ->> 'resourceId')::uuid as legislative_act_id
            from tiles t
            where nodegroupid = archaeological_site.node_alias_uuid('authority')
              and t.resourceinstanceid = p_resourceinstanceid
              and tiledata -> archaeological_site.node_alias_uuid('legislative_act')::text is not null
        ),
        authorities as (
            select resourceinstanceid,
                   tiledata -> legislative_act.node_alias_uuid('authority')::text -> 0 -> 'labels' -> 0 ->> 'value' as authority
            from tiles
            where nodegroupid = legislative_act.node_alias_uuid('authority')
        ),
        registration_status as (
            select resourceinstanceid,
                   tiledata->(archaeological_site.node_alias_uuid('decision_registration_status')::text)->0->'labels'->0->>'value' status
            from tiles where
                           resourceinstanceid = p_resourceinstanceid and
                nodegroupid = archaeological_site.node_alias_uuid('site_decision')
                       order by tiledata->>archaeological_site.node_alias_uuid('decision_date')::text desc limit 1
        )
        select jsonb_build_object(
            'authorities', coalesce(array_agg(distinct a.authority) filter (where a.authority is not null), '{}'::text[]),
            'borden_number', bn.borden_number,
            'registration_status', rs.status
        )
        into data
        from bcap.public.resource_instances ri
            left join borden_number bn on ri.resourceinstanceid = bn.resourceinstanceid
             left join arch_site_leg_acts hs on hs.resourceinstanceid = ri.resourceinstanceid
             left join authorities a on a.resourceinstanceid = hs.legislative_act_id
             left join registration_status rs on rs.resourceinstanceid = ri.resourceinstanceid
        where ri.resourceinstanceid = p_resourceinstanceid
        group by ri.resourceinstanceid, bn.borden_number, rs.status;

    end if;
    return data;
end;
$$
    language plpgsql;
