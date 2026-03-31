drop function if exists get_map_attribute_data;
create or replace function get_map_attribute_data(p_resourceinstanceid uuid, nodeid uuid) returns jsonb as
    $$
declare
    l_arch_site_geom_node_id text = 'b18223c2-13ef-11f0-8695-0242ac170007';
    l_arch_site_legislative_act_id text = '034d2e02-13f2-11f0-9ff8-0242ac170007';

    l_borden_number_id text = '7e15332c-1c54-11f0-b5bf-0242ac170007';
    l_borden_numer_nodegroup_id text = '034d1c32-13f2-11f0-9ff8-0242ac170007';

    l_leg_act_authority_node_id text = '7789d580-3b87-11ee-a701-080027b7463b';
    data jsonb;
begin
    if nodeid = l_arch_site_geom_node_id::uuid then -- Archaeological Site

        with borden_number as (
            select resourceinstanceid,
                   tiledata ->> l_borden_number_id as borden_number
            from tiles
            where nodegroupid = l_borden_numer_nodegroup_id::uuid
              and resourceinstanceid = p_resourceinstanceid
        ),
        arch_site_leg_acts as (
            select t.resourceinstanceid,
                   (jsonb_array_elements(tiledata -> l_arch_site_legislative_act_id) ->> 'resourceId')::uuid as legislative_act_id
            from tiles t
            where nodegroupid = '034d1fac-13f2-11f0-9ff8-0242ac170007'::uuid
              and t.resourceinstanceid = p_resourceinstanceid
              and tiledata -> l_arch_site_legislative_act_id is not null
        ),
        authorities as (
            select resourceinstanceid,
                   tiledata -> l_leg_act_authority_node_id -> 0 -> 'labels' -> 0 ->> 'value' as authority
            from tiles
            where nodegroupid = '7789d580-3b87-11ee-a701-080027b7463b'::uuid
        )
        select jsonb_build_object(
            'authorities', coalesce(array_agg(distinct a.authority) filter (where a.authority is not null), '{}'::text[]),
            'borden_number', bn.borden_number
        )
        into data
        from borden_number bn
             left join arch_site_leg_acts hs on hs.resourceinstanceid = bn.resourceinstanceid
             left join authorities a on a.resourceinstanceid = hs.legislative_act_id
        where bn.resourceinstanceid = p_resourceinstanceid
        group by bn.resourceinstanceid, bn.borden_number;

    end if;
    return data;
end;
$$
    language plpgsql;
