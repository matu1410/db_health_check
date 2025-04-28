SELECT s.sid, s.username, s.event, s.status, s.wait_class, s.sql_id,
       s.seconds_in_wait, s.module, TO_CHAR(s.logon_time, 'DD/MM/YYYY HH24:MI') AS logon_time
FROM v$session s
WHERE s.status = 'ACTIVE'
  AND s.seconds_in_wait > 1800
  AND s.username IS NOT NULL
ORDER BY s.seconds_in_wait DESC