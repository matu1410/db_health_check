SELECT df.tablespace_name,
       ROUND(SUM(df.bytes)/1024/1024, 2),
       ROUND(SUM(df.bytes - NVL(fs.bytes,0))/1024/1024, 2),
       ROUND(NVL(fs.bytes,0)/1024/1024, 2),
       ROUND((SUM(df.bytes - NVL(fs.bytes,0)) / SUM(df.bytes)) * 100, 2)
FROM dba_data_files df
LEFT JOIN (
    SELECT tablespace_name, SUM(bytes) AS bytes
    FROM dba_free_space
    GROUP BY tablespace_name
) fs ON df.tablespace_name = fs.tablespace_name
GROUP BY df.tablespace_name, fs.bytes
ORDER BY 5 DESC