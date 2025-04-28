SELECT name,
       CEIL(space_limit / 1024 / 1024) AS size_mb,
       CEIL(space_used / 1024 / 1024) AS used_mb,
       ROUND((space_used / space_limit) * 100, 2) AS pct_used
FROM V$RECOVERY_FILE_DEST