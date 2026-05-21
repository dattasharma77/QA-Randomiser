"""
Snowflake queries for QA Randomizer auto-refresh.
Date range: month start to CURRENT_DATE - 2 (covers all weeks up to today).
"""

def get_alerts_query(month_start: str, agent_list: list, month_end: str = None) -> str:
    """
    Build the alerts SQL with account category column.
    Includes category_history CTE to get old/new account category per alert.
    month_start = 'YYYY-MM-01'
    month_end   = 'YYYY-MM-DD' — if None, uses CURRENT_DATE - 2
    """
    agents_sql = ",".join(f"'{a}'" for a in agent_list)
    end_clause = f"'{month_end}'" if month_end else "CURRENT_DATE - 2"
    return f"""
WITH category_history AS (
    SELECT
        x.player_id,
        x.effective_from_timestamp,
        cc_new.Cashier_Category_Desc AS new_category,
        COALESCE(cc_old.Cashier_Category_Desc, 'NewUser') AS old_category
    FROM (
        SELECT
            player_id,
            wh_cashier_category_cd,
            effective_from_timestamp,
            LAG(wh_cashier_category_cd) OVER (
                PARTITION BY player_id
                ORDER BY effective_from_timestamp
            ) AS old_wh_cashier_category_cd
        FROM EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.Cashier_Category_Log
    ) x
    LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.Dim_Cashier_Category cc_new
        ON cc_new.wh_cashier_category_cd = x.wh_cashier_category_cd
    LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.Dim_Cashier_Category cc_old
        ON cc_old.wh_cashier_category_cd = x.old_wh_cashier_category_cd
)
SELECT
    a12.src_player_alert_sk        AS ALERT_ID,
    a12.Alert_Creation_Date,
    a12.update_date                AS UPDATE_DATE,
    a12.src_resolved_by_agent_id   AS SRC_RESOLVED_BY_AGENT_ID,
    a15.Front_End_Cd               AS FRONT_END_CD,
    a17.Src_Alert_Type_CD          AS ALERT_TYPE_DESC,
    a14.Country_CD                 AS COUNTRY_CD,
    a12.comments                   AS COMMENTS,
    a12.LOGIN_NAME_TXT,
    a22.Src_Alert_Resolution_CD,
    -- Current account category at time of alert resolution
    MAX(CASE WHEN a10.new_status_cd = 'alt_resolved'
             THEN cat.new_category END)  AS ACC_CATEGORY,
    CASE
        WHEN a12.Src_Resolved_By_Agent_ID IN (
            'Abhay.Kumar','Abhishek.Sarkar','Arshiya.Fathima2','akatta','BGurung.Tik',
            'B.NitheeshKumar','Buyakar.kumar','mbaig2','Mohammad.Azharuddin','Mohd.Imranuddin',
            'Muddhanollu.Suresh2','Mulugu.Prashanth','nikitha.Chitteti','Nishitha.Puneria',
            'PLavanya2','Prathamesh.Patil','rmysore','Ramji.Kumar','rpalli','reshmi.mehta',
            'rohith.paramati','jagadeesh.narahari','Saiprakashraj.B','Samanvitha.Karri',
            'S.UdhayKumar','Sohail.Khan','Soniya.Tiwari','Soumya.Jena','Sowmya.Mallaram',
            'sravan.kandukuru','sdumpala','peddi.srikanth','Thota.Subramanyam','Supratim.Sen',
            'Vasanth.Nannuri','zeba.naz','akatkar','arun.jatoth','balraj.vastrala','B.Yadav',
            'kiranmayee.gundeti','shaikhashan.basha','Karishma.Mohammad','Sunny.Katta',
            'Kulvinder.Singh','mohammad.ali','Mubeen.Wajeed','naveen.avuti','Netha.Divya',
            'Pooja.Mahanand','Raghu.K','Rohan.Sharma3','Taruni.Agarwal','Goswami.Abhishek',
            'A.DheerajGoud','Balraj.Dhami','bprudhvikalyan','Himani.Sharma','jayachandra.pasupula',
            'Harishankar.Achuthan','Makili.Snehith','Mammidala.Sharanya','mdheer','Matam.Vishal',
            'sairam.medicharla','harika.minegeri','Mohammad.muqeeth','myalala','Munnuri.VenuKumar',
            'Nadari.Govardhan','psasidharan','P.Bishwakarma','S.Trichinapally','skanduru',
            'SriTeja.Kallepu','Swamy.Talari','Bharath.Uppari','V.Kappagantu','Arpan.Vasudev',
            'A.Keerthana','Keerthana.Dasa','G.Reddy','Sanjana.Patlola','S.Gundabatthni2',
            'Sowmya.Sayanedi','V.Manoor','Nandini.Kumari2','Akshay.Kumar3','Awinash.Singh',
            'Soma.Keertana','Pooja.Nagare','HM.PavanKumar','Raju.Singha','ChSrividya.Tapaswi',
            'P.Danthinada','Hemanth.Pridvi','S.Mohammed2','Akshay.Tomar','Sri.Hasini',
            'Saumya.Singh','Boya.Nagarjuna','Preethi.Kothapeta'
        ) THEN 'ENTAIN'
        WHEN a12.Src_Resolved_By_Agent_ID IN (
            'Chanda.Deepthi','Akhil.Chintapatla','Chitram.Bhavani','Geetha.Lanke',
            'GhataniVinod.Kumar','K.Raju','Himadri.Kumari','joshna.sadula','Margam.Bhavani',
            'Punna.Raj','R.Ramakrishna','shivashankar.satta','Rakesh.Shobaram',
            'BobbalaVarun.Kumar','Zoya.Naz','Chandana.pendem','Deepak.chavvakula',
            'Gouthami.Bobbili','Haridas.Haritha','Chaithanya.Kasa','Sampath.Mailavaram',
            'manasa.motaparti','Nithin.Biradar','Reeshika.Sharma','Niharika.Tammala',
            'Likhita.Banka','Nithinkanth.Dasyam','kalpana.Dhamala','Mahananda.Math',
            'kolanupaka.mahesh','Medi.Kalyan','MohdArifNawaz.Khan','Muskan.Begum',
            'Piyush.Devda','Podila.Vardhan','Pramodh.Pucha','Chandrakala.Rasala',
            'Rishabh.Aggarwal','Swapna.Punna','Aishwarya.Varaganti','V.Lingidi',
            'Karuna.Eda','Vyshnavi.S'
        ) THEN 'LCG'
        WHEN a12.Src_Resolved_By_Agent_ID IN (
            'Vinay.Sheru','Shiva.Tipparaju','Srikanth.Kurakula','Priyanka.Avirneni',
            'Chandrakant.Likhit','M.Meghana','AliciaMary.Frantz','kiran.gonna','naveen.bandaru'
        ) THEN 'LATAM'
        WHEN a12.Src_Resolved_By_Agent_ID IN (
            'Aakash.Jaiswal','Rajesh.Akula','H.Gattikoppula','Kishmathi.Arjun',
            'Vejerla.Likhitha','Turerao.kumar','RaviKiran.Vissa','Aravind.Meka',
            'Asma.Fathima','Gurrala.Kiran','Lakshmi.Nayak','Vineeth.Nadikatla',
            'Ramadasu.Kumar','Rubina.Tabassum','Sakshi.Mishra'
        ) THEN 'GERMAN'
        ELSE 'EUROBET'
    END AS TEAM
FROM   EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.player_alert a12
    LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.player_alert_log a10
        ON a10.wh_player_alert_id = a12.wh_player_alert_id
    LEFT OUTER JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.agent a13
        ON (a12.Resolved_By_Agent_ID = a13.Agent_ID)
    LEFT OUTER JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.dim_player a15
        ON (a12.PLAYER_ID = a15.PLAYER_ID)
    LEFT OUTER JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.alert_type a17
        ON (a12.WH_Alert_Type_CD = a17.WH_Alert_Type_CD)
    LEFT OUTER JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.dim_front_end a18
        ON (a15.Front_End_CD = a18.Front_End_CD)
    LEFT OUTER JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.player a14
        ON (a12.Player_ID = a14.Player_ID)
    LEFT OUTER JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.alert_resolution a22
        ON (a12.WH_Alert_Resolution_CD = a22.WH_Alert_Resolution_CD)
    LEFT OUTER JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.DIM_COUNTRY dc
        ON (dc.COUNTRY_CD = a14.COUNTRY_CD)
    -- Join category history to get account category at time of alert
    LEFT JOIN category_history cat
        ON cat.player_id = a12.player_id
        AND cat.effective_from_timestamp = (
            SELECT MAX(c2.effective_from_timestamp)
            FROM EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.Cashier_Category_Log c2
            WHERE c2.player_id = a12.player_id
              AND c2.effective_from_timestamp <= a10.effective_from_timestamp
        )
WHERE a12.update_date BETWEEN '{month_start}' AND {end_clause}
AND a17.Src_Alert_Type_CD NOT IN ('contact', 'contact_rmc')
AND a12.src_resolved_by_agent_id IN ({agents_sql})
GROUP BY 1,2,3,4,5,6,7,8,9,10,12
"""


def get_pending_redeems_query(month_start: str, agent_list: list, month_end: str = None) -> str:
    """
    Pull redeemvrfn alerts that are:
    - Pending (alt_pending) and not handled within 7 days
    - Resolved (alt_resolved) cashout requests
    - Denied cashout requests
    These are merged into the alerts pool for sampling.
    """
    agents_sql = ",".join(f"'{a}'" for a in agent_list)
    end_clause = f"'{month_end}'" if month_end else "CURRENT_DATE - 2"
    return f"""
SELECT
    a12.WH_PLAYER_ALERT_ID         AS ALERT_ID,
    p.LOGIN_NAME_TXT,
    a12.SRC_RESOLVED_BY_AGENT_ID,
    a12.PLAYER_ID,
    a17.SRC_ALERT_TYPE_CD          AS ALERT_TYPE_DESC,
    a22.SRC_ALERT_RESOLUTION_CD,
    a12.LAST_UPD_TIMESTAMP         AS UPDATE_DATE,
    a12.Alert_Creation_Date,
    CASE
        WHEN a12.SRC_RESOLVED_BY_AGENT_ID IN (
            'Abhay.Kumar','Abhishek.Sarkar','Arshiya.Fathima2','akatta','BGurung.Tik',
            'B.NitheeshKumar','Buyakar.kumar','mbaig2','Mohammad.Azharuddin','Mohd.Imranuddin',
            'Muddhanollu.Suresh2','Mulugu.Prashanth','nikitha.Chitteti','Nishitha.Puneria',
            'PLavanya2','Prathamesh.Patil','rmysore','Ramji.Kumar','rpalli','reshmi.mehta',
            'rohith.paramati','jagadeesh.narahari','Saiprakashraj.B','Samanvitha.Karri',
            'S.UdhayKumar','Sohail.Khan','Soniya.Tiwari','Soumya.Jena','Sowmya.Mallaram',
            'sravan.kandukuru','sdumpala','peddi.srikanth','Thota.Subramanyam','Supratim.Sen',
            'Vasanth.Nannuri','zeba.naz','akatkar','arun.jatoth','balraj.vastrala','B.Yadav',
            'kiranmayee.gundeti','shaikhashan.basha','Karishma.Mohammad','Sunny.Katta',
            'Kulvinder.Singh','mohammad.ali','Mubeen.Wajeed','naveen.avuti','Netha.Divya',
            'Pooja.Mahanand','Raghu.K','Rohan.Sharma3','Taruni.Agarwal','Goswami.Abhishek',
            'A.DheerajGoud','Balraj.Dhami','bprudhvikalyan','Himani.Sharma','jayachandra.pasupula',
            'Harishankar.Achuthan','Makili.Snehith','Mammidala.Sharanya','mdheer','Matam.Vishal',
            'sairam.medicharla','harika.minegeri','Mohammad.muqeeth','myalala','Munnuri.VenuKumar',
            'Nadari.Govardhan','psasidharan','P.Bishwakarma','S.Trichinapally','skanduru',
            'SriTeja.Kallepu','Swamy.Talari','Bharath.Uppari','V.Kappagantu','Arpan.Vasudev',
            'A.Keerthana','Keerthana.Dasa','G.Reddy','Sanjana.Patlola','S.Gundabatthni2',
            'Sowmya.Sayanedi','V.Manoor','Nandini.Kumari2','Akshay.Kumar3','Awinash.Singh',
            'Soma.Keertana','Pooja.Nagare','HM.PavanKumar','Raju.Singha','ChSrividya.Tapaswi',
            'P.Danthinada','Hemanth.Pridvi','S.Mohammed2','Akshay.Tomar','Sri.Hasini',
            'Saumya.Singh','Boya.Nagarjuna','Preethi.Kothapeta'
        ) THEN 'ENTAIN'
        WHEN a12.SRC_RESOLVED_BY_AGENT_ID IN (
            'Chanda.Deepthi','Akhil.Chintapatla','Chitram.Bhavani','Geetha.Lanke',
            'GhataniVinod.Kumar','K.Raju','Himadri.Kumari','joshna.sadula','Margam.Bhavani',
            'Punna.Raj','R.Ramakrishna','shivashankar.satta','Rakesh.Shobaram',
            'BobbalaVarun.Kumar','Zoya.Naz','Chandana.pendem','Deepak.chavvakula',
            'Gouthami.Bobbili','Haridas.Haritha','Chaithanya.Kasa','Sampath.Mailavaram',
            'manasa.motaparti','Nithin.Biradar','Reeshika.Sharma','Niharika.Tammala',
            'Likhita.Banka','Nithinkanth.Dasyam','kalpana.Dhamala','Mahananda.Math',
            'kolanupaka.mahesh','Medi.Kalyan','MohdArifNawaz.Khan','Muskan.Begum',
            'Piyush.Devda','Podila.Vardhan','Pramodh.Pucha','Chandrakala.Rasala',
            'Rishabh.Aggarwal','Swapna.Punna','Aishwarya.Varaganti','V.Lingidi',
            'Karuna.Eda','Vyshnavi.S'
        ) THEN 'LCG'
        WHEN a12.SRC_RESOLVED_BY_AGENT_ID IN (
            'Vinay.Sheru','Shiva.Tipparaju','Srikanth.Kurakula','Priyanka.Avirneni',
            'Chandrakant.Likhit','M.Meghana','AliciaMary.Frantz','kiran.gonna','naveen.bandaru'
        ) THEN 'LATAM'
        WHEN a12.SRC_RESOLVED_BY_AGENT_ID IN (
            'Aakash.Jaiswal','Rajesh.Akula','H.Gattikoppula','Kishmathi.Arjun',
            'Vejerla.Likhitha','Turerao.kumar','RaviKiran.Vissa','Aravind.Meka',
            'Asma.Fathima','Gurrala.Kiran','Lakshmi.Nayak','Vineeth.Nadikatla',
            'Ramadasu.Kumar','Rubina.Tabassum','Sakshi.Mishra'
        ) THEN 'GERMAN'
        ELSE 'EUROBET'
    END AS TEAM
FROM EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.PLAYER_ALERT a12
LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.ALERT_TYPE a17
    ON a12.WH_ALERT_TYPE_CD = a17.WH_ALERT_TYPE_CD
LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.ALERT_RESOLUTION a22
    ON a12.WH_ALERT_RESOLUTION_CD = a22.WH_ALERT_RESOLUTION_CD
LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.PLAYER p
    ON a12.PLAYER_ID = p.PLAYER_ID
WHERE a17.SRC_ALERT_TYPE_CD = 'redeemvrfn'
AND (
    -- Pending redeems not handled within 7 days
    (a22.SRC_ALERT_RESOLUTION_CD = 'alt_pending'
     AND DATEDIFF('day', a12.Alert_Creation_Date, CURRENT_DATE) > 7)
    OR
    -- Resolved cashout requests
    a22.SRC_ALERT_RESOLUTION_CD = 'alt_resolved'
    OR
    -- Closed/denied cashout requests (rdm_closed is the denied equivalent)
    a22.SRC_ALERT_RESOLUTION_CD IN ('rdm_closed', 'alt_failed', 'alt_expired')
)
AND a12.LAST_UPD_TIMESTAMP BETWEEN '{month_start}' AND {end_clause}
AND a12.src_resolved_by_agent_id IN ({agents_sql})
"""


def get_zendesk_query(month_start: str, zendesk_agent_list: list, month_end: str = None,
                      name_list: list = None) -> str:
    """
    Build the Zendesk SQL. Already filtered to Risk teams via COLLATE like '%Risk%'.
    Includes both original names AND reversed first/last name variants to handle
    cases where Snowflake has 'Goswami Abhishek' but bracketing has 'Abhishek Goswami'.
    """
    def reverse_name(name):
        """Reverse first/last name: 'Abhishek Goswami' -> 'Goswami Abhishek'"""
        parts = str(name).strip().split()
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}"
        return name  # 3+ word names: don't reverse

    # Build comprehensive name list: original + reversed variants
    all_names_set = set()
    for n in (zendesk_agent_list or []):
        s = str(n).strip()
        if s and s.lower() != 'nan':
            all_names_set.add(s)
            all_names_set.add(reverse_name(s))
    for n in (name_list or []):
        s = str(n).strip()
        if s and s.lower() != 'nan':
            all_names_set.add(s)
            all_names_set.add(reverse_name(s))

    all_names = sorted(all_names_set)
    agents_sql = ",".join(f"'{a}'" for a in all_names)
    end_clause = f"'{month_end}'" if month_end else "CURRENT_DATE - 2"
    return f"""
WITH main AS (
    SELECT DISTINCT
        te.id, te.ticket_id, timestamp1,
        DATE(te.timestamp1) AS upd_date,
        ua."ROLE" AS agent_role,
        CASE WHEN ua."ROLE" = 'agent' THEN ua.NAME ELSE ua2.name END AS agent_name
    FROM EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_ticket_events te
    LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_ticket_events_child_events ce
        ON te.id = ce.id
    LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_users ua
        ON ua.id = te.updater_id
    LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_users ua2
        ON ua2.id = ce.child_events_assignee_id
    WHERE DATE(te.timestamp1) BETWEEN '{month_start}' AND {end_clause}
    AND ua.name IN ({agents_sql})
),
upg AS (
    SELECT DISTINCT id, ticket_id, created_at, brand_name, agent_name, Ticket_group AS teams
    FROM (
        SELECT DISTINCT id, ticket_id, created_at, update_date, agent_name, brand_name,
            Ticket_group, R1
        FROM (
            SELECT DISTINCT a.id, a.ticket_id, a.CREATED_AT,
                DATE(a.CREATED_AT) update_date, brand_name, a.ce_id,
                agent_name,
                LAST_VALUE(a.name) IGNORE NULLS OVER (
                    PARTITION BY a.ticket_id
                    ORDER BY a.CREATED_AT ASC, a.id, ce_id ASC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) Ticket_group,
                ROW_NUMBER() OVER (
                    PARTITION BY a.ticket_id, a.id
                    ORDER BY a.CREATED_AT DESC, a.id DESC, a.ce_id DESC
                ) AS R1
            FROM (
                SELECT DISTINCT a.id, a.ticket_id, a.CREATED_AT, g.NAME,
                    b.child_events_id AS ce_id,
                    zu2.name AS agent_name,
                    br.name AS brand_name
                FROM EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_ticket_events a
                LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_ticket_events_child_events b
                    ON a.ticket_id = b.ticket_id AND a.id = b.id
                LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_groups g
                    ON b.child_events_group_id = g.id
                LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_users zu2
                    ON zu2.id = a.updater_id
                LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.ZENDESK_TICKETS t
                    ON t.id = a.ticket_id
                LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.ZENDESK_BRANDS br
                    ON br.id = t.brand_id
                WHERE a.TICKET_ID IN (SELECT DISTINCT ticket_id FROM main)
                ORDER BY a.ticket_id, a.CREATED_AT, a.id
            ) AS a
            ORDER BY a.ticket_id, a.CREATED_AT, a.id, a.ce_id
        )
        WHERE R1 = 1
        ORDER BY 2,3,1
    )
    WHERE DATE(CREATED_AT) IN (SELECT DISTINCT upd_date FROM main)
    ORDER BY 1,2,3
),
channel AS (
    SELECT DISTINCT ticket_id, channel
    FROM (
        SELECT te.ticket_id,
            csf.custom_field_options_name AS channel,
            ROW_NUMBER() OVER (
                PARTITION BY te.ticket_id
                ORDER BY te.timestamp1 DESC, tef.child_events_id DESC
            ) AS row_count
        FROM EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_ticket_events te
        INNER JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_ticket_events_custom_fields tef
            ON te.id = tef.id
        LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_ticket_fields_custom_field_options csf
            ON tef.child_events_custom_ticket_field_value = csf.custom_field_options_value
            AND tef.child_events_custom_ticket_field_id = csf.id
        WHERE tef.child_events_custom_ticket_field_id = 4414414558737
        AND te.ticket_id IN (SELECT ticket_id FROM main)
    )
    WHERE row_count = 1
),
category AS (
    SELECT *
    FROM (
        SELECT DISTINCT cf.ticket_id,
            cfo.custom_field_options_name AS category_full_path,
            ROW_NUMBER() OVER (
                PARTITION BY cf.ticket_id ORDER BY cf.child_events_id DESC
            ) AS row_count
        FROM EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_ticket_events te
        LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_ticket_events_custom_fields cf
            ON te.id = cf.id
        LEFT JOIN EDLDIGITALVIEWS.EDLDIGITALVIEWSBI.zendesk_ticket_fields_custom_field_options cfo
            ON cf.child_events_custom_ticket_field_value = cfo.custom_field_options_value
            AND cf.child_events_custom_ticket_field_id IN (6469544440337, 7630497177105)
        WHERE cfo.custom_field_options_name IS NOT NULL
        AND cf.ticket_id IN (SELECT ticket_id FROM main)
    )
    WHERE row_count = 1
)
SELECT DISTINCT
    main.agent_name                                     AS AGENT_NAME,
    upg.teams                                           AS UPDATE_TICKET_GROUP,
    main.ticket_id                                      AS TICKET_ID,
    upg.brand_name                                      AS TICKET_BRAND,
    DATE(upg.CREATED_AT)                                AS UPDATE_DATE,
    channel.channel                                     AS CHANNEL,
    cg.category_full_path                               AS CATEGORY_FULL_PATH
FROM main
LEFT JOIN upg
    ON upg.ticket_id = main.ticket_id
    AND upg.agent_name = main.agent_name
    AND main.timestamp1 = upg.created_at
LEFT JOIN channel ON channel.ticket_id = main.ticket_id
LEFT JOIN category cg ON cg.ticket_id = main.ticket_id
WHERE main.agent_role = 'agent'
AND upg.agent_name IN ({agents_sql})
AND COLLATE(teams, 'en-ci') LIKE '%Risk%'
GROUP BY 1,2,3,4,5,6,7
ORDER BY 1
"""


# --- Archive table queries for persistent frozen picks storage ---

ARCHIVE_TABLE = "QA_FROZEN_ARCHIVE"
ARCHIVE_SCHEMA = "EDLDIGITALVIEWSBI"
ARCHIVE_DB = "EDLDIGITALVIEWS"
ARCHIVE_FULL = f"{ARCHIVE_DB}.{ARCHIVE_SCHEMA}.{ARCHIVE_TABLE}"


def get_create_archive_table_sql():
    """SQL to create the archive table if it doesn't exist."""
    return f"""
CREATE TABLE IF NOT EXISTS {ARCHIVE_FULL} (
    RECORD_TYPE       VARCHAR(10),    -- 'alerts' or 'zendesk'
    MONTH             VARCHAR(7),     -- 'YYYY-MM'
    WEEK              VARCHAR(10),    -- 'Week 1', 'Week 2', etc.
    AGENT_ID          VARCHAR(200),   -- SRC_RESOLVED_BY_AGENT_ID or AGENT_NAME
    AGENT_NAME        VARCHAR(200),
    TL                VARCHAR(200),
    QA_BRACKET        NUMBER,
    ITEM_ID           VARCHAR(50),    -- ALERT_ID or TICKET_ID
    ALERT_TYPE_DESC   VARCHAR(100),
    SAMPLE_CATEGORY   VARCHAR(20),    -- Alerts, BV, Redeems, Zendesk
    UPDATE_DATE       VARCHAR(30),
    FROZEN_AT         VARCHAR(30),
    LOGIN_NAME_TXT    VARCHAR(200),
    EXTRA_JSON        VARCHAR(5000),  -- any other fields as JSON
    INSERTED_AT       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
"""


def get_insert_archive_sql(records: list) -> str:
    """Build INSERT statement for archive records."""
    if not records:
        return ""

    def esc(val):
        if val is None:
            return "NULL"
        s = str(val).replace("'", "''")
        return f"'{s}'"

    rows = []
    for r in records:
        row = (
            esc(r.get("record_type", "")),
            esc(r.get("Month", "")),
            esc(r.get("Week", "")),
            esc(r.get("SRC_RESOLVED_BY_AGENT_ID", r.get("AGENT_NAME", ""))),
            esc(r.get("AgentName", "")),
            esc(r.get("TL", "")),
            str(r.get("QA_BRACKET", "NULL")),
            esc(r.get("ALERT_ID", r.get("TICKET_ID", ""))),
            esc(r.get("ALERT_TYPE_DESC", "")),
            esc(r.get("SampleCategory", "")),
            esc(r.get("UPDATE_DATE", "")),
            esc(r.get("FrozenAt", "")),
            esc(r.get("LOGIN_NAME_TXT", "")),
            esc(""),  # EXTRA_JSON placeholder
        )
        rows.append(f"({','.join(row)})")

    # Snowflake supports multi-row INSERT up to ~16MB
    # Batch in chunks of 500
    statements = []
    for i in range(0, len(rows), 500):
        batch = rows[i:i+500]
        stmt = f"""INSERT INTO {ARCHIVE_FULL}
(RECORD_TYPE, MONTH, WEEK, AGENT_ID, AGENT_NAME, TL, QA_BRACKET,
 ITEM_ID, ALERT_TYPE_DESC, SAMPLE_CATEGORY, UPDATE_DATE, FROZEN_AT,
 LOGIN_NAME_TXT, EXTRA_JSON)
VALUES {','.join(batch)}"""
        statements.append(stmt)
    return statements


def get_load_archive_sql(month: str = None) -> str:
    """SQL to load archive records, optionally filtered by month."""
    where = f"WHERE MONTH = '{month}'" if month else ""
    return f"SELECT * FROM {ARCHIVE_FULL} {where} ORDER BY MONTH DESC, WEEK, AGENT_NAME"


def get_check_existing_sql(month: str, week: str, record_type: str) -> str:
    """Check if records already exist for a given month/week/type."""
    return f"""
SELECT COUNT(*) AS cnt FROM {ARCHIVE_FULL}
WHERE MONTH = '{month}' AND WEEK = '{week}' AND RECORD_TYPE = '{record_type}'
"""
