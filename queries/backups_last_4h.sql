SELECT TO_CHAR(start_time, 'DD/MM/YYYY HH24:MI') AS start_time,
       TO_CHAR(end_time, 'DD/MM/YYYY HH24:MI') AS end_time,
       ROUND(output_bytes/1024/1024) AS output_mb,
       status,
       input_type
FROM V$RMAN_BACKUP_JOB_DETAILS
WHERE start_time >= SYSDATE - (4/24)
ORDER BY start_time DESC