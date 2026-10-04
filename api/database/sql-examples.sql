-- =====================================================================
-- 教務系統 SQL 操作範例
--
-- 對應系統中各功能背後的查詢，可直接執行：
--   mysql -u academic_app -p academic_db < api/database/sql-examples.sql
--
-- 所有會修改資料的範例都包在交易內並以 ROLLBACK 結尾，不會改動資料。
-- 註：Windows 版 MySQL 預設 lower_case_table_names=1，表名不分大小寫；
--     Linux 版會區分，因此本檔一律使用與 schema 相同的 PascalCase 表名。
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. 多表 JOIN + GROUP_CONCAT：本學期開課清單（學生「加退選」頁）
--    一個班可能有多位教師、多個時段，用 GROUP_CONCAT 收斂成一列
-- ---------------------------------------------------------------------
SELECT
    s.section_id,
    c.course_no,
    c.course_name,
    c.credit,
    GROUP_CONCAT(DISTINCT t.teacher_name ORDER BY st.is_primary DESC SEPARATOR '、') AS teachers,
    s.capacity
FROM Section s
JOIN Semester sem       ON sem.semester_id = s.semester_id AND sem.is_current = TRUE
JOIN Course c           ON c.course_no = s.course_no
JOIN SectionTeacher st  ON st.section_id = s.section_id
JOIN Teacher t          ON t.teacher_id = st.teacher_id
WHERE s.status = 'Open'
GROUP BY s.section_id, c.course_no, c.course_name, c.credit, s.capacity
ORDER BY c.course_no;

-- 同樣的需求改用 View：v_section_detail 已封裝 JOIN 與計數邏輯
SELECT section_id, course_name, teacher_names, schedule_text,
       enrolled_count, capacity, capacity - enrolled_count AS remaining
FROM v_section_detail
WHERE semester_id = '1151' AND status = 'Open'
ORDER BY course_no;


-- ---------------------------------------------------------------------
-- 2. 為什麼 View 用「相關子查詢」而不是一路 JOIN？（fan-out 陷阱）
--    統計學習有 2 位教師 × 3 個時段，直接 JOIN 再 COUNT 會把人數放大 6 倍
-- ---------------------------------------------------------------------
SELECT s.section_id, COUNT(*) AS wrong_count            -- 錯誤：66 = 11 人 × 2 教師 × 3 時段
FROM Section s
JOIN SectionTeacher st  ON st.section_id = s.section_id
JOIN SectionSchedule ss ON ss.section_id = s.section_id
JOIN Enrollment e       ON e.section_id = s.section_id AND e.status IN ('Selected', 'Manual')
WHERE s.section_id = 3
GROUP BY s.section_id;

SELECT section_id, enrolled_count AS correct_count       -- 正確：11
FROM v_section_detail
WHERE section_id = 3;


-- ---------------------------------------------------------------------
-- 3. 聚合函式：歷年開課紀錄（某課程每學期的教師、修課人數、平均、及格率）
-- ---------------------------------------------------------------------
SELECT
    v.semester_id,
    v.course_name,
    v.teacher_names,
    v.enrolled_count,
    ROUND(AVG(e.score), 1)                                         AS avg_score,
    ROUND(100 * SUM(e.score >= IF(stu.degree = 1, 70, 60)) / COUNT(e.score), 1) AS pass_rate_pct
FROM v_section_detail v
LEFT JOIN Enrollment e  ON e.section_id = v.section_id AND e.status IN ('Selected', 'Manual')
LEFT JOIN Student stu   ON stu.student_id = e.student_id
WHERE v.course_no = 'A0002'
GROUP BY v.section_id, v.semester_id, v.course_name, v.teacher_names, v.enrolled_count
ORDER BY v.semester_id DESC;


-- ---------------------------------------------------------------------
-- 4. CTE + 加權平均：學生歷年成績單（學分加權平均、實得學分）
-- ---------------------------------------------------------------------
WITH graded AS (
    SELECT student_id, semester_id, credit, score, passed
    FROM v_student_transcript
    WHERE student_id = 'S001'
)
SELECT
    semester_id,
    SUM(credit)                                                   AS credits_taken,
    SUM(CASE WHEN passed = 1 THEN credit ELSE 0 END)              AS credits_earned,
    ROUND(SUM(score * credit) / NULLIF(SUM(CASE WHEN score IS NOT NULL THEN credit END), 0), 2) AS weighted_avg
FROM graded
GROUP BY semester_id WITH ROLLUP;                                 -- 最後一列（semester_id 為 NULL）為歷年總計


-- ---------------------------------------------------------------------
-- 5. 視窗函式（Window Function）：每班成績排名與 PR 值
-- ---------------------------------------------------------------------
SELECT
    c.course_name,
    e.student_id,
    e.score,
    RANK()         OVER (PARTITION BY e.section_id ORDER BY e.score DESC)      AS rank_in_class,
    ROUND(100 * PERCENT_RANK() OVER (PARTITION BY e.section_id ORDER BY e.score), 0) AS pr
FROM Enrollment e
JOIN Section s ON s.section_id = e.section_id
JOIN Course c  ON c.course_no = s.course_no
WHERE s.semester_id = '1132' AND e.score IS NOT NULL AND s.course_no IN ('A0003', 'A0007')
ORDER BY c.course_name, rank_in_class;


-- ---------------------------------------------------------------------
-- 6. 衝堂檢查：S012 已選統計學（五234），若再加選 section 12（計算機概論 二34、五4）會在五4 衝堂
--    元組比較 (weekday, period) IN (子查詢) 是 MySQL 支援的寫法
-- ---------------------------------------------------------------------
SELECT c.course_name, mine.weekday, mine.period
FROM SectionSchedule mine
JOIN Enrollment e ON e.section_id = mine.section_id
JOIN Section s    ON s.section_id = mine.section_id
JOIN Course c     ON c.course_no = s.course_no
WHERE e.student_id = 'S012'
  AND e.status IN ('Selected', 'Manual')
  AND mine.semester_id = '1151'
  AND (mine.weekday, mine.period) IN (
        SELECT weekday, period FROM SectionSchedule WHERE section_id = 12);


-- ---------------------------------------------------------------------
-- 7. NOT EXISTS：本學期還沒選任何課的在學學生（可用於選課提醒）
-- ---------------------------------------------------------------------
SELECT stu.student_id, stu.student_name, d.dept_name
FROM Student stu
JOIN Department d ON d.dept_id = stu.dept_id
WHERE stu.status = 'Enrolled'
  AND NOT EXISTS (
        SELECT 1
        FROM Enrollment e
        JOIN Section s ON s.section_id = e.section_id
        WHERE e.student_id = stu.student_id
          AND s.semester_id = '1151'
          AND e.status IN ('Selected', 'Manual'))
ORDER BY stu.student_id;


-- ---------------------------------------------------------------------
-- 8. 教室使用率：每間教室在本學期被排了幾節課（LEFT JOIN 保留沒被使用的教室）
-- ---------------------------------------------------------------------
SELECT b.building_name, r.room_code, COUNT(ss.schedule_id) AS periods_used
FROM Room r
JOIN Building b              ON b.building_id = r.building_id
LEFT JOIN SectionSchedule ss ON ss.room_code = r.room_code AND ss.semester_id = '1151'
GROUP BY b.building_name, r.room_code
ORDER BY periods_used DESC, r.room_code;


-- ---------------------------------------------------------------------
-- 9. 交易 + 悲觀鎖：先搶先贏加選（api/app/services/enrollment_service.py 的 SQL 版）
--    S004 加選 section 16（演算法，上限 3、已選 2）
-- ---------------------------------------------------------------------
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
START TRANSACTION;

-- (1) 鎖學生列：同一位學生的加退選請求依序執行
SELECT student_id, status FROM Student WHERE student_id = 'S004' FOR UPDATE;

-- (2) 鎖班級列：搶同一班的請求在此排隊，直到前一個交易 COMMIT / ROLLBACK
SELECT section_id, capacity, status FROM Section WHERE section_id = 16 FOR UPDATE;

-- (3) 持有鎖的情況下計算名額，確保不會超收
SELECT COUNT(*) INTO @enrolled
FROM Enrollment WHERE section_id = 16 AND status IN ('Selected', 'Manual');

-- (4) 名額足夠才寫入（應用程式中由程式判斷，這裡用 INSERT ... SELECT 表達條件）
INSERT INTO Enrollment (student_id, section_id, status)
SELECT 'S004', 16, 'Selected'
FROM Section
WHERE section_id = 16 AND @enrolled < capacity;

SELECT ROW_COUNT() AS inserted, @enrolled AS enrolled_before;

ROLLBACK;   -- 範例不保留變更；實際系統為 COMMIT


-- ---------------------------------------------------------------------
-- 10. 交易確保一致性：切換開課權限 + 寫入稽核紀錄必須同時成功或同時失敗
-- ---------------------------------------------------------------------
START TRANSACTION;

UPDATE Teacher SET can_open_section = TRUE WHERE teacher_id = 'T002';

INSERT INTO TeacherPermissionLog (teacher_id, granted, changed_by)
SELECT 'T002', TRUE, user_id FROM UserAccount WHERE username = 'admin';

SELECT t.teacher_id, t.can_open_section, l.granted, l.changed_at
FROM Teacher t
JOIN TeacherPermissionLog l ON l.teacher_id = t.teacher_id
WHERE t.teacher_id = 'T002';

ROLLBACK;


-- ---------------------------------------------------------------------
-- 11. 約束示範（取消註解執行，會被資料庫拒絕）
-- ---------------------------------------------------------------------
-- CHECK 約束：成績必須介於 0–100
-- UPDATE Enrollment SET score = 120 WHERE student_id = 'S001' AND section_id = 1;
--   → ERROR 3819: Check constraint 'chk_enrollment_score' is violated.

-- UNIQUE 約束：同學期同教室同時段不可重複（L102 在 1151 的星期三第 2 節已被演算法使用）
-- INSERT INTO SectionSchedule (section_id, semester_id, room_code, weekday, period)
-- VALUES (11, '1151', 'L102', 3, 2);
--   → ERROR 1062: Duplicate entry '1151-L102-3-2' for key 'SectionSchedule.uq_room_timeslot'

-- 複合外鍵：時段的學期必須與班級一致（section 11 屬於 1151，不能掛到 1132）
-- INSERT INTO SectionSchedule (section_id, semester_id, room_code, weekday, period)
-- VALUES (11, '1132', 'O313', 6, 1);
--   → ERROR 1452: Cannot add or update a child row: a foreign key constraint fails
