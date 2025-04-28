SELECT TO_CHAR(start_time, 'DD/MM/YYYY HH24:MI') AS start_time,
       status,
       input_type
FROM V$RMAN_BACKUP_JOB_DETAILS
WHERE status = 'RUNNING'
ORDER BY start_time DESC