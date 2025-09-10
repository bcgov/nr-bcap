create or replace function __arches_get_node_value_sql(node nodes) returns text as
$$
declare
    node_value_sql text;
    select_sql     text = '(t.tiledata->>%L)';
    datatype       text = 'text';
begin
    select_sql = format(select_sql, node.nodeid);
    if (node.config ->> 'pgDatatype' is not null) then
        datatype = node.config ->> 'pgDatatype';
    else
        case node.datatype
            when 'geojson-feature-collection' then datatype = 'geometry';
            when 'string' then datatype = 'jsonb';
            when 'number' then datatype = 'numeric';
            when 'boolean' then datatype = 'boolean';
            when 'resource-instance' then datatype = 'jsonb';
            when 'resource-instance-list' then datatype = 'jsonb';
            when 'annotation' then datatype = 'jsonb';
            when 'file-list' then datatype = 'jsonb';
            when 'url' then datatype = 'jsonb';
            when 'date' then datatype = 'timestamp';
            when 'node-value' then datatype = 'uuid';
            when 'domain-value' then datatype = 'uuid';
            when 'domain-value-list' then datatype = 'uuid[]';
            when 'concept' then datatype = 'uuid';
            when 'concept-list' then datatype = 'uuid[]';
            when 'reference' then datatype = 'jsonb';
            else datatype = 'text';
            end case;
    end if;
    case datatype
        when 'geometry' then select_sql = format('
                                st_collect(
                                    array(
                                        select st_transform(geom, 4326) from geojson_geometries
                                        where geojson_geometries.tileid = t.tileid and nodeid = %L
                                    )
                                )',
                                                 node.nodeid
                                          );
        when 'timestamp' then select_sql = format(
                'to_date(
                    t.tiledata->>%L::text,
                    %L
                )',
                node.nodeid,
                node.config ->> 'dateFormat'
                                           );
        when 'uuid[]' then select_sql = format('(
                                    CASE
                                        WHEN t.tiledata->>%1$L is null THEN null
                                        ELSE ARRAY(
                                            SELECT jsonb_array_elements_text(
                                                t.tiledata->%1$L
                                            )::uuid
                                        )
                                    END
                                )', node.nodeid
                                        );
        else null;
        end case;


    node_value_sql = format(
            '%s::%s as "%s"',
            select_sql,
            datatype,
            __arches_slugify(node.name)
                     );
    return node_value_sql;
end
$$ language plpgsql volatile;