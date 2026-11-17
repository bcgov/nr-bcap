drop function if exists databc.html_to_plain_string cascade;
create or replace function databc.html_to_plain_string(string_to_clean text) returns text as
$$
declare
    result text;
begin
    result := string_to_clean;

    -- Block-level opening tags: start a new line before the enclosed content.
    result := regexp_replace(result, '<(p|div|h[1-6])[^>]*>', E'\n', 'gi');
    -- <br> variants: newline.
    result := regexp_replace(result, E'<br\\s*/?>', E'\n', 'gi');
    -- List items: bullet on its own line.
    result := regexp_replace(result, '<li[^>]*>', E'\n- ', 'gi');

    -- Strip all remaining tags (closing block tags, inline tags, attributes).
    result := regexp_replace(result, '<[^>]*>', '', 'g');

    -- Decode common HTML entities; &amp; last to avoid double-decoding
    -- (e.g. &amp;lt; should become &lt;, not <).
    result := replace(result, '&nbsp;', ' ');
    result := replace(result, '&lt;',   '<');
    result := replace(result, '&gt;',   '>');
    result := replace(result, '&quot;', '"');
    result := replace(result, '&#39;',  '''');
    result := replace(result, '&amp;',  '&');

    -- Collapse runs of blank lines to a single blank line, and extra spaces.
    result := regexp_replace(result, E'\n{3,}', E'\n\n', 'g');
    result := regexp_replace(result, ' {2,}', ' ', 'g');

    return left(trim(E'\n\r\t ' from result), 4000);
end
$$ language plpgsql;
ALTER FUNCTION databc.html_to_plain_string(string_to_clean text) SECURITY DEFINER SET search_path = public;
