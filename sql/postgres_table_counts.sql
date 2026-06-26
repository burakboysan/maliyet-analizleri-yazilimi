select
  schemaname || '.' || relname as table,
  n_live_tup::bigint as row_count
from pg_stat_user_tables
order by schemaname, relname;
