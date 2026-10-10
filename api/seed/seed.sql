-- =====================================================================
-- 種子資料（由 python -m seed 逐句執行；帳號與密碼雜湊由 seed/__main__.py 產生）
-- 切分規則：以「行尾分號」切分敘述，字串內不可出現分號或 --
--
-- 1132 學期：完整轉換自原 insert_data.sql
--   * Course 的 capacity / status 移到 Section
--   * CourseSchedule.time_slot '一5' 拆為 weekday = 1、period = 5
--   * CourseTeacher 改為 SectionTeacher
--   * CourseSelection 改為 Enrollment，'Dropped'（落選）改為 'NotSelected'
--   * 時段與原資料不同：計算機概論的「五 4」改為「五 5」、經濟學改為「二 567」，
--     使已結束學期的有效選課沒有學生衝堂（衝堂只出現在目前學期的選課操作中）
-- 1131 學期：歷史學期，比 1132 更早的修課紀錄
-- 1141 學期：新增的歷史學期，用來展示「同一門課、不同學期、不同教師」
-- 1142 學期：歷史學期，含同一門課在同學期開兩班（線性代數 01／02）
-- 1151 學期：目前學期（選課中），供加退選與開課展示
-- 1152 學期：下學期（規劃中），只有開課資料、沒有選課，含一個已停開的班級
-- 課程 A0011～A0020 與其各學期班級、選課集中寫在檔案末段
-- =====================================================================

-- ---------------------------------------------------------------------
-- 基礎資料（沿用原檔）
-- ---------------------------------------------------------------------
INSERT INTO Department (dept_id, dept_name) VALUES
('D001', '數學系'),
('D002', '資訊工程系'),
('D003', '資訊管理系');

INSERT INTO Teacher (teacher_id, teacher_name, dept_id, can_open_section) VALUES
('T001', '岳飛', NULL, TRUE),
('T002', '陸羽', NULL, FALSE),
('T003', '劉邦', NULL, TRUE),
('T004', '項羽', NULL, FALSE),
('T005', '孔丘', NULL, FALSE),
('T006', '莊周', NULL, FALSE),
('T007', '巴哈', NULL, FALSE),
('T008', '達文西', NULL, FALSE);

INSERT INTO Building (building_id, building_name) VALUES
('B001', '綜教館'),
('B002', '工程五館'),
('B003', '鴻經館'),
('B004', '管理二館');

INSERT INTO Room (room_code, building_id, seat_capacity) VALUES
('O313', 'B001', 60),
('L102', 'B002', 60),
('M-605', 'B003', 60),
('I1-018', 'B004', 60),
('I1-304', 'B004', 60),
('O-214', 'B001', 120);

INSERT INTO Student (student_id, student_name, dept_id, grade, status, class_code, degree) VALUES
('S001', '張飛', 'D001', 1, 'Enrolled', 'A', 0),
('S002', '孫尚香', 'D001', 1, 'Suspended', 'A', 0),
('S003', '周瑜', 'D001', 1, 'Enrolled', 'A', 0),
('S004', '黃蓋', 'D001', 1, 'Enrolled', 'A', 0),
('S005', '趙雲', 'D001', 1, 'Enrolled', 'A', 0),
('S006', '關興', 'D001', 1, 'Enrolled', 'A', 0),
('S007', '夏侯惇', 'D001', 1, 'Enrolled', 'A', 0),
('S008', '龐統', 'D002', 1, 'Suspended', 'A', 0),
('S009', '關羽', 'D002', 1, 'Enrolled', 'A', 0),
('S010', '華雄', 'D002', 1, 'Dropped', 'A', 1),
('S011', '華陀', 'D002', 1, 'Enrolled', 'A', 1),
('S012', '劉備', 'D003', 1, 'Enrolled', 'A', 0),
('S013', '呂布', 'D002', 1, 'Enrolled', 'A', 1),
('S014', '諸葛亮', 'D002', 1, 'Enrolled', 'A', 1),
('S015', '呂蒙', 'D002', 1, 'Enrolled', 'A', 1),
('S016', '圖靈', 'D001', 1, 'Enrolled', 'A', 1),
('S017', '巴斯卡', 'D001', 1, 'Enrolled', 'A', 1),
('S018', '大喬', 'D002', 1, 'Enrolled', 'A', 0),
('S019', '甘寧', 'D002', 1, 'Enrolled', 'A', 0),
('S020', '司馬昭', 'D002', 1, 'Enrolled', 'A', 0),
('S021', '馬超', 'D002', 1, 'Enrolled', 'A', 0),
('S022', '郭嘉', 'D002', 1, 'Enrolled', 'A', 1);

-- 課程庫：capacity、status 已移至 Section（A0011～A0020 見檔案末段）
INSERT INTO Course (course_no, course_name, course_type, credit) VALUES
('A0001', '日文', 'Elective', 2),
('A0002', '計算機概論', 'Required', 3),
('A0003', '統計學習', 'Elective', 3),
('A0004', '經濟學', 'Required', 3),
('A0005', '統計學', 'Elective', 3),
('A0006', '音樂欣賞', 'Elective', 2),
('A0007', '演算法', 'Elective', 3),
('A0008', '線性代數', 'Required', 3),
('A0009', '資料庫系統', 'Required', 3),
('A0010', '西洋美術史', 'Elective', 2);

INSERT INTO CurriculumField (course_no, field_name) VALUES
('A0001', '語言'),
('A0002', '基礎知識'),
('A0002', '人工智慧'),
('A0003', '財務工程'),
('A0003', '統計推論'),
('A0004', '基礎知識'),
('A0005', '基礎知識'),
('A0006', '人文思想'),
('A0007', '人工智慧'),
('A0007', '資料科學'),
('A0008', '理論數學'),
('A0008', '基礎知識'),
('A0009', '基礎知識'),
('A0009', '資料科學'),
('A0010', '人文思想');

-- ---------------------------------------------------------------------
-- 學期
-- ---------------------------------------------------------------------
INSERT INTO Semester (semester_id, acad_year, term, status, is_current) VALUES
('1131', 113, 1, 'Finished', FALSE),
('1132', 113, 2, 'Finished', FALSE),
('1141', 114, 1, 'Finished', FALSE),
('1142', 114, 2, 'Finished', FALSE),
('1151', 115, 1, 'Enrolling', TRUE),
('1152', 115, 2, 'Planning', FALSE);

-- ---------------------------------------------------------------------
-- 1131 學期（歷史資料）：section_id 17~21，各班時段互不重疊
-- ---------------------------------------------------------------------
INSERT INTO Section (section_id, course_no, semester_id, section_code, capacity, status, created_by) VALUES
(17, 'A0002', '1131', '01', 50, 'Open', NULL),
(18, 'A0004', '1131', '01', 50, 'Open', NULL),
(19, 'A0008', '1131', '01', 50, 'Open', 'T001'),
(20, 'A0006', '1131', '01', 100, 'Open', NULL),
(21, 'A0007', '1131', '01', 50, 'Open', NULL);

INSERT INTO SectionTeacher (section_id, teacher_id, is_primary) VALUES
(17, 'T002', TRUE),
(18, 'T005', TRUE),
(19, 'T001', TRUE),
(20, 'T007', TRUE),
(21, 'T008', TRUE);

INSERT INTO SectionSchedule (section_id, semester_id, room_code, weekday, period) VALUES
(17, '1131', 'L102', 1, 2), (17, '1131', 'L102', 1, 3), (17, '1131', 'L102', 1, 4),
(18, '1131', 'I1-018', 2, 5), (18, '1131', 'I1-018', 2, 6), (18, '1131', 'I1-018', 2, 7),
(19, '1131', 'O313', 3, 2), (19, '1131', 'O313', 3, 3), (19, '1131', 'O313', 3, 4),
(20, '1131', 'O-214', 4, 5), (20, '1131', 'O-214', 4, 6),
(21, '1131', 'M-605', 5, 2), (21, '1131', 'M-605', 5, 3), (21, '1131', 'M-605', 5, 4);

INSERT INTO Enrollment (student_id, section_id, status, score, feedback_rank) VALUES
-- A0002 計算機概論
('S003', 17, 'Selected', 82, 8),
('S005', 17, 'Selected', 71, 6),
('S009', 17, 'Selected', 88, 9),
('S011', 17, 'Selected', 59, 4),
('S013', 17, 'Selected', 76, 7),
('S018', 17, 'Selected', 64, 6),
-- A0004 經濟學
('S001', 18, 'Selected', 68, 5),
('S004', 18, 'Selected', 73, 7),
('S007', 18, 'Selected', 81, 8),
('S012', 18, 'Selected', 90, 9),
('S019', 18, 'Selected', 52, 3),
-- A0008 線性代數
('S003', 19, 'Selected', 77, 7),
('S014', 19, 'Selected', 93, 10),
('S015', 19, 'Manual', 62, 6),
('S016', 19, 'Selected', 95, 9),
('S017', 19, 'Selected', 84, 8),
('S022', 19, 'Selected', 70, 6),
-- A0006 音樂欣賞
('S001', 20, 'Selected', 85, 9),
('S005', 20, 'Selected', 91, 10),
('S006', 20, 'Selected', 79, 8),
('S012', 20, 'Withdrawn', NULL, NULL),
('S020', 20, 'Selected', 88, 9),
('S021', 20, 'Selected', 74, 7),
-- A0007 演算法
('S011', 21, 'Selected', 73, 6),
('S013', 21, 'Selected', 58, 4),
('S014', 21, 'Selected', 86, 8),
('S016', 21, 'Selected', 92, 9);

-- ---------------------------------------------------------------------
-- 1132 學期（轉換自原資料）：section_id 1~7 對應 A0001~A0007
-- ---------------------------------------------------------------------
INSERT INTO Section (section_id, course_no, semester_id, section_code, capacity, status) VALUES
(1, 'A0001', '1132', '01', 50, 'Open'),
(2, 'A0002', '1132', '01', 50, 'Open'),
(3, 'A0003', '1132', '01', 50, 'Open'),
(4, 'A0004', '1132', '01', 50, 'Open'),
(5, 'A0005', '1132', '01', 50, 'Open'),
(6, 'A0006', '1132', '01', 100, 'Open'),
(7, 'A0007', '1132', '01', 50, 'Open');

INSERT INTO SectionTeacher (section_id, teacher_id, is_primary) VALUES
(1, 'T001', TRUE),
(2, 'T002', TRUE),
(3, 'T003', TRUE),
(3, 'T004', FALSE),
(4, 'T005', TRUE),
(5, 'T006', TRUE),
(6, 'T007', TRUE),
(7, 'T008', TRUE);

-- weekday：一=1 二=2 三=3 四=4 五=5
INSERT INTO SectionSchedule (section_id, semester_id, room_code, weekday, period) VALUES
(1, '1132', 'O313', 1, 5), (1, '1132', 'O313', 1, 6), (1, '1132', 'O313', 1, 7),
(2, '1132', 'L102', 2, 3), (2, '1132', 'L102', 2, 4), (2, '1132', 'L102', 5, 5),
(3, '1132', 'M-605', 4, 5), (3, '1132', 'M-605', 4, 6), (3, '1132', 'M-605', 4, 7),
(4, '1132', 'I1-018', 2, 5), (4, '1132', 'I1-018', 2, 6), (4, '1132', 'I1-018', 2, 7),
(5, '1132', 'I1-304', 5, 2), (5, '1132', 'I1-304', 5, 3), (5, '1132', 'I1-304', 5, 4),
(6, '1132', 'O-214', 3, 5), (6, '1132', 'O-214', 3, 6),
(7, '1132', 'L102', 3, 2), (7, '1132', 'L102', 3, 3), (7, '1132', 'L102', 3, 4);

INSERT INTO Enrollment (student_id, section_id, status, score, feedback_rank) VALUES
-- A0001 日文
('S001', 1, 'Selected', 77.7, 6),
('S002', 1, 'Selected', NULL, NULL),
('S003', 1, 'Selected', 56, 2),
('S004', 1, 'Selected', 34, 5),
('S005', 1, 'Selected', 98, 7),
('S006', 1, 'Selected', 55, 10),
('S007', 1, 'Selected', 67, 2),
('S008', 1, 'Selected', NULL, NULL),
-- A0002 計算機概論
('S009', 2, 'Selected', 66, 5),
('S008', 2, 'Selected', NULL, NULL),
('S003', 2, 'Selected', 93, 7),
('S004', 2, 'Selected', 44, 3),
('S005', 2, 'Selected', 49, 10),
('S007', 2, 'Selected', 78, 5),
('S010', 2, 'Selected', NULL, NULL),
('S011', 2, 'Selected', 74, 10),
-- A0003 統計學習
('S008', 3, 'Selected', NULL, NULL),
('S001', 3, 'Selected', 46, 10),
('S004', 3, 'Selected', 76, 7),
('S006', 3, 'Selected', 87, 10),
('S012', 3, 'NotSelected', NULL, NULL),
('S010', 3, 'Selected', NULL, NULL),
('S013', 3, 'Selected', 76, 7),
('S011', 3, 'Selected', 80, 10),
('S014', 3, 'Selected', 78, 5),
('S015', 3, 'Selected', 65, 7),
('S016', 3, 'Selected', 99, 5),
('S017', 3, 'Manual', 69, 1),
-- A0004 經濟學
('S008', 4, 'NotSelected', NULL, NULL),
('S001', 4, 'Selected', 56.5, 5),
('S002', 4, 'Selected', NULL, NULL),
('S004', 4, 'Selected', 67.5, 10),
('S005', 4, 'Selected', 78, 7),
('S007', 4, 'Selected', 89, 2),
('S013', 4, 'Selected', 45, 7),
-- A0005 統計學
('S009', 5, 'Selected', 68.7, 1),
('S018', 5, 'Selected', 63, 7),
('S019', 5, 'Selected', 31, 10),
('S002', 5, 'Selected', NULL, NULL),
('S003', 5, 'Selected', 78, 2),
('S004', 5, 'Selected', 87, 10),
('S012', 5, 'Selected', 96, 2),
-- A0006 音樂欣賞
('S009', 6, 'Selected', 76, 7),
('S008', 6, 'Selected', NULL, NULL),
('S020', 6, 'NotSelected', NULL, NULL),
('S021', 6, 'NotSelected', NULL, NULL),
('S001', 6, 'Selected', 34, 5),
('S002', 6, 'NotSelected', NULL, NULL),
('S003', 6, 'NotSelected', NULL, NULL),
('S004', 6, 'Selected', 80, 7),
('S006', 6, 'Selected', 62, 10),
('S007', 6, 'Selected', 44, 5),
('S012', 6, 'Selected', 56, 10),
('S010', 6, 'Selected', NULL, NULL),
('S011', 6, 'Selected', 98, 7),
('S014', 6, 'Selected', 55, 10),
('S015', 6, 'Selected', 78, 9),
-- A0007 演算法
('S001', 7, 'NotSelected', NULL, NULL),
('S010', 7, 'Selected', NULL, NULL),
('S013', 7, 'Selected', 79, 8),
('S022', 7, 'Selected', 87, 7),
('S011', 7, 'Selected', 68, 5),
('S008', 7, 'Selected', NULL, NULL),
('S016', 7, 'Selected', 99, 5),
('S017', 7, 'Selected', 69.5, 10);

-- ---------------------------------------------------------------------
-- 1141 學期（新增的歷史資料）：同課程換老師，展示歷年開課查詢
-- ---------------------------------------------------------------------
INSERT INTO Section (section_id, course_no, semester_id, section_code, capacity, status, created_by) VALUES
(8, 'A0002', '1141', '01', 50, 'Open', NULL),
(9, 'A0006', '1141', '01', 100, 'Open', NULL),
(10, 'A0005', '1141', '01', 50, 'Open', 'T003');

INSERT INTO SectionTeacher (section_id, teacher_id, is_primary) VALUES
(8, 'T008', TRUE),
(9, 'T007', TRUE),
(10, 'T003', TRUE);

INSERT INTO SectionSchedule (section_id, semester_id, room_code, weekday, period) VALUES
(8, '1141', 'L102', 2, 3), (8, '1141', 'L102', 2, 4), (8, '1141', 'L102', 5, 5),
(9, '1141', 'O-214', 3, 5), (9, '1141', 'O-214', 3, 6),
(10, '1141', 'I1-304', 5, 2), (10, '1141', 'I1-304', 5, 3), (10, '1141', 'I1-304', 5, 4);

INSERT INTO Enrollment (student_id, section_id, status, score, feedback_rank) VALUES
('S001', 8, 'Selected', 72, 8),
('S012', 8, 'Selected', 85, 9),
('S018', 8, 'Selected', 58, 6),
('S019', 8, 'Selected', 64, 7),
('S003', 9, 'Selected', 91, 10),
('S020', 9, 'Selected', 70, 8),
('S021', 9, 'Selected', 66, 7),
('S001', 10, 'Selected', 61, 6),
('S006', 10, 'Selected', 83, 9),
('S014', 10, 'Selected', 74, 8);

-- ---------------------------------------------------------------------
-- 1142 學期（歷史資料）：section_id 22~27
--   線性代數同學期開兩班（section 26 為 01 班、section 27 為 02 班）
--   統計學習改由項羽主授、劉邦協同（1132 為劉邦主授）
-- ---------------------------------------------------------------------
INSERT INTO Section (section_id, course_no, semester_id, section_code, capacity, status, created_by) VALUES
(22, 'A0009', '1142', '01', 60, 'Open', 'T003'),
(23, 'A0001', '1142', '01', 50, 'Open', NULL),
(24, 'A0003', '1142', '01', 40, 'Open', NULL),
(25, 'A0010', '1142', '01', 80, 'Open', NULL),
(26, 'A0008', '1142', '01', 50, 'Open', NULL),
(27, 'A0008', '1142', '02', 50, 'Open', 'T001');

INSERT INTO SectionTeacher (section_id, teacher_id, is_primary) VALUES
(22, 'T003', TRUE),
(23, 'T001', TRUE),
(24, 'T004', TRUE),
(24, 'T003', FALSE),
(25, 'T007', TRUE),
(26, 'T006', TRUE),
(27, 'T001', TRUE);

INSERT INTO SectionSchedule (section_id, semester_id, room_code, weekday, period) VALUES
(22, '1142', 'I1-304', 2, 2), (22, '1142', 'I1-304', 2, 3), (22, '1142', 'I1-304', 2, 4),
(23, '1142', 'O313', 1, 5), (23, '1142', 'O313', 1, 6), (23, '1142', 'O313', 1, 7),
(24, '1142', 'M-605', 4, 5), (24, '1142', 'M-605', 4, 6), (24, '1142', 'M-605', 4, 7),
(25, '1142', 'O-214', 3, 5), (25, '1142', 'O-214', 3, 6),
(26, '1142', 'L102', 5, 2), (26, '1142', 'L102', 5, 3), (26, '1142', 'L102', 5, 4),
(27, '1142', 'M-605', 1, 2), (27, '1142', 'M-605', 1, 3), (27, '1142', 'M-605', 1, 4);

INSERT INTO Enrollment (student_id, section_id, status, score, feedback_rank) VALUES
-- A0009 資料庫系統
('S009', 22, 'Selected', 87, 9),
('S011', 22, 'Selected', 79, 7),
('S013', 22, 'Selected', 66, 6),
('S014', 22, 'Selected', 91, 10),
('S015', 22, 'Selected', 72, 7),
('S018', 22, 'Selected', 58, 5),
('S019', 22, 'Selected', 63, 6),
('S022', 22, 'Selected', 85, 8),
-- A0001 日文
('S003', 23, 'Selected', 74, 7),
('S004', 23, 'Selected', 61, 5),
('S006', 23, 'Selected', 88, 9),
('S007', 23, 'Selected', 69, 6),
('S021', 23, 'Selected', 77, 8),
-- A0003 統計學習
('S011', 24, 'Manual', 70, 6),
('S012', 24, 'NotSelected', NULL, NULL),
('S013', 24, 'Selected', 81, 8),
('S016', 24, 'Selected', 96, 10),
('S017', 24, 'Selected', 75, 7),
-- A0010 西洋美術史
('S001', 25, 'Selected', 79, 8),
('S005', 25, 'Selected', 83, 8),
('S006', 25, 'Withdrawn', NULL, NULL),
('S020', 25, 'Selected', 92, 10),
('S021', 25, 'Selected', 68, 6),
-- A0008 線性代數 01 班
('S003', 26, 'Selected', 71, 7),
('S004', 26, 'Selected', 55, 4),
('S005', 26, 'Selected', 64, 6),
-- A0008 線性代數 02 班
('S009', 27, 'Selected', 82, 8),
('S012', 27, 'Selected', 77, 7),
('S018', 27, 'Selected', 69, 6);

-- ---------------------------------------------------------------------
-- 1151 學期（目前學期、選課中）
--   section 14（統計學 五234）與 section 12（計算機概論 五4）衝堂，可用來展示衝堂檢查
--   section 16（演算法）人數上限 3、已選 2 人，可用來展示額滿與併發搶課
-- ---------------------------------------------------------------------
INSERT INTO Section (section_id, course_no, semester_id, section_code, capacity, status, created_by) VALUES
(11, 'A0001', '1151', '01', 50, 'Open', 'T001'),
(12, 'A0002', '1151', '01', 50, 'Open', NULL),
(13, 'A0003', '1151', '01', 40, 'Open', 'T003'),
(14, 'A0005', '1151', '01', 50, 'Open', NULL),
(15, 'A0006', '1151', '01', 100, 'Open', NULL),
(16, 'A0007', '1151', '01', 3, 'Open', NULL);

INSERT INTO SectionTeacher (section_id, teacher_id, is_primary) VALUES
(11, 'T001', TRUE),
(12, 'T002', TRUE),
(13, 'T003', TRUE),
(13, 'T004', FALSE),
(14, 'T006', TRUE),
(15, 'T007', TRUE),
(16, 'T008', TRUE);

INSERT INTO SectionSchedule (section_id, semester_id, room_code, weekday, period) VALUES
(11, '1151', 'O313', 1, 5), (11, '1151', 'O313', 1, 6), (11, '1151', 'O313', 1, 7),
(12, '1151', 'L102', 2, 3), (12, '1151', 'L102', 2, 4), (12, '1151', 'L102', 5, 4),
(13, '1151', 'M-605', 4, 5), (13, '1151', 'M-605', 4, 6), (13, '1151', 'M-605', 4, 7),
(14, '1151', 'I1-304', 5, 2), (14, '1151', 'I1-304', 5, 3), (14, '1151', 'I1-304', 5, 4),
(15, '1151', 'O-214', 3, 5), (15, '1151', 'O-214', 3, 6),
(16, '1151', 'L102', 3, 2), (16, '1151', 'L102', 3, 3), (16, '1151', 'L102', 3, 4);

INSERT INTO Enrollment (student_id, section_id, status) VALUES
('S001', 11, 'Selected'),
('S001', 15, 'Selected'),
('S003', 12, 'Selected'),
('S003', 16, 'Selected'),
('S013', 16, 'Selected'),
('S022', 13, 'Selected'),
('S009', 12, 'Selected'),
('S009', 15, 'Selected'),
('S012', 14, 'Selected');

-- ---------------------------------------------------------------------
-- 1152 學期（下學期、規劃中）：section_id 28~33，尚未開放選課，因此沒有選課資料
--   section 33（西洋美術史）為已停開班級：停開時會刪除時段以釋放教室，所以不寫入 SectionSchedule
-- ---------------------------------------------------------------------
INSERT INTO Section (section_id, course_no, semester_id, section_code, capacity, status, created_by) VALUES
(28, 'A0002', '1152', '01', 60, 'Open', NULL),
(29, 'A0009', '1152', '01', 60, 'Open', 'T003'),
(30, 'A0008', '1152', '01', 50, 'Open', 'T001'),
(31, 'A0004', '1152', '01', 50, 'Open', NULL),
(32, 'A0006', '1152', '01', 100, 'Open', NULL),
(33, 'A0010', '1152', '01', 80, 'Cancelled', NULL);

INSERT INTO SectionTeacher (section_id, teacher_id, is_primary) VALUES
(28, 'T002', TRUE),
(29, 'T003', TRUE),
(30, 'T001', TRUE),
(31, 'T005', TRUE),
(32, 'T007', TRUE),
(33, 'T007', TRUE);

INSERT INTO SectionSchedule (section_id, semester_id, room_code, weekday, period) VALUES
(28, '1152', 'L102', 1, 2), (28, '1152', 'L102', 1, 3), (28, '1152', 'L102', 1, 4),
(29, '1152', 'I1-304', 2, 2), (29, '1152', 'I1-304', 2, 3), (29, '1152', 'I1-304', 2, 4),
(30, '1152', 'O313', 3, 2), (30, '1152', 'O313', 3, 3), (30, '1152', 'O313', 3, 4),
(31, '1152', 'I1-018', 4, 5), (31, '1152', 'I1-018', 4, 6), (31, '1152', 'I1-018', 4, 7),
(32, '1152', 'O-214', 3, 5), (32, '1152', 'O-214', 3, 6);

-- =====================================================================
-- 新增課程 A0011～A0020：課程庫、領域、各學期班級與選課（section_id 34~53）
--   本學期 1151：section 34~43，每門課一班，部分學生已選（尚無成績）
--   歷史學期：section 44~53，含成績與教學評量；微積分在 1131、1141 由不同教師開設
--   各學期內教室時段不重複、教師不重複授課、學生的有效選課不衝堂
-- =====================================================================
INSERT INTO Course (course_no, course_name, course_type, credit) VALUES
('A0011', '微積分', 'Required', 4),
('A0012', '離散數學', 'Required', 3),
('A0013', '機率論', 'Required', 3),
('A0014', '機器學習', 'Elective', 3),
('A0015', '作業系統', 'Required', 3),
('A0016', '計算機網路', 'Elective', 3),
('A0017', '英文寫作', 'Elective', 2),
('A0018', '投資學', 'Elective', 3),
('A0019', '哲學概論', 'Elective', 2),
('A0020', '資料視覺化', 'Elective', 2);

INSERT INTO CurriculumField (course_no, field_name) VALUES
('A0011', '理論數學'),
('A0011', '基礎知識'),
('A0012', '理論數學'),
('A0013', '統計推論'),
('A0013', '理論數學'),
('A0014', '人工智慧'),
('A0014', '資料科學'),
('A0015', '基礎知識'),
('A0016', '基礎知識'),
('A0017', '語言'),
('A0018', '財務工程'),
('A0019', '人文思想'),
('A0020', '資料科學');

-- 1151（目前學期）：section 34~43
INSERT INTO Section (section_id, course_no, semester_id, section_code, capacity, status, created_by) VALUES
(34, 'A0011', '1151', '01', 60, 'Open', 'T001'),
(35, 'A0012', '1151', '01', 50, 'Open', NULL),
(36, 'A0013', '1151', '01', 40, 'Open', NULL),
(37, 'A0014', '1151', '01', 30, 'Open', 'T003'),
(38, 'A0015', '1151', '01', 50, 'Open', NULL),
(39, 'A0016', '1151', '01', 50, 'Open', NULL),
(40, 'A0017', '1151', '01', 40, 'Open', NULL),
(41, 'A0018', '1151', '01', 60, 'Open', NULL),
(42, 'A0019', '1151', '01', 80, 'Open', NULL),
(43, 'A0020', '1151', '01', 30, 'Open', NULL);

-- 1131～1142（歷史學期）：section 44~53
INSERT INTO Section (section_id, course_no, semester_id, section_code, capacity, status, created_by) VALUES
(44, 'A0011', '1131', '01', 60, 'Open', 'T001'),
(45, 'A0017', '1131', '01', 40, 'Open', NULL),
(46, 'A0012', '1132', '01', 50, 'Open', NULL),
(47, 'A0019', '1132', '01', 80, 'Open', NULL),
(48, 'A0011', '1141', '01', 60, 'Open', NULL),
(49, 'A0013', '1141', '01', 40, 'Open', 'T003'),
(50, 'A0015', '1141', '01', 50, 'Open', NULL),
(51, 'A0014', '1142', '01', 30, 'Open', 'T003'),
(52, 'A0016', '1142', '01', 50, 'Open', NULL),
(53, 'A0018', '1142', '01', 60, 'Open', NULL);

INSERT INTO SectionTeacher (section_id, teacher_id, is_primary) VALUES
(34, 'T001', TRUE),
(35, 'T008', TRUE),
(36, 'T006', TRUE),
(37, 'T003', TRUE),
(37, 'T004', FALSE),
(38, 'T002', TRUE),
(39, 'T008', TRUE),
(40, 'T005', TRUE),
(41, 'T004', TRUE),
(42, 'T006', TRUE),
(43, 'T007', TRUE),
(44, 'T001', TRUE),
(45, 'T005', TRUE),
(46, 'T008', TRUE),
(47, 'T006', TRUE),
(48, 'T006', TRUE),
(49, 'T003', TRUE),
(50, 'T002', TRUE),
(51, 'T003', TRUE),
(51, 'T004', FALSE),
(52, 'T008', TRUE),
(53, 'T004', TRUE);

INSERT INTO SectionSchedule (section_id, semester_id, room_code, weekday, period) VALUES
(34, '1151', 'O313', 2, 5), (34, '1151', 'O313', 2, 6), (34, '1151', 'O313', 4, 2), (34, '1151', 'O313', 4, 3),
(35, '1151', 'M-605', 1, 2), (35, '1151', 'M-605', 1, 3), (35, '1151', 'M-605', 1, 4),
(36, '1151', 'I1-304', 1, 5), (36, '1151', 'I1-304', 1, 6), (36, '1151', 'I1-304', 1, 7),
(37, '1151', 'M-605', 5, 5), (37, '1151', 'M-605', 5, 6), (37, '1151', 'M-605', 5, 7),
(38, '1151', 'L102', 4, 2), (38, '1151', 'L102', 4, 3), (38, '1151', 'L102', 4, 4),
(39, '1151', 'L102', 2, 5), (39, '1151', 'L102', 2, 6), (39, '1151', 'L102', 2, 7),
(40, '1151', 'O-214', 1, 2), (40, '1151', 'O-214', 1, 3),
(41, '1151', 'I1-018', 3, 2), (41, '1151', 'I1-018', 3, 3), (41, '1151', 'I1-018', 3, 4),
(42, '1151', 'O-214', 4, 2), (42, '1151', 'O-214', 4, 3),
(43, '1151', 'I1-304', 5, 5), (43, '1151', 'I1-304', 5, 6),
(44, '1131', 'O313', 1, 5), (44, '1131', 'O313', 1, 6), (44, '1131', 'O313', 4, 2), (44, '1131', 'O313', 4, 3),
(45, '1131', 'I1-304', 3, 5), (45, '1131', 'I1-304', 3, 6),
(46, '1132', 'M-605', 1, 2), (46, '1132', 'M-605', 1, 3), (46, '1132', 'M-605', 1, 4),
(47, '1132', 'O-214', 4, 2), (47, '1132', 'O-214', 4, 3),
(48, '1141', 'O313', 1, 2), (48, '1141', 'O313', 1, 3), (48, '1141', 'O313', 3, 2), (48, '1141', 'O313', 3, 3),
(49, '1141', 'M-605', 4, 5), (49, '1141', 'M-605', 4, 6), (49, '1141', 'M-605', 4, 7),
(50, '1141', 'I1-018', 2, 5), (50, '1141', 'I1-018', 2, 6), (50, '1141', 'I1-018', 2, 7),
(51, '1142', 'L102', 3, 2), (51, '1142', 'L102', 3, 3), (51, '1142', 'L102', 3, 4),
(52, '1142', 'I1-018', 4, 2), (52, '1142', 'I1-018', 4, 3), (52, '1142', 'I1-018', 4, 4),
(53, '1142', 'O-214', 5, 5), (53, '1142', 'O-214', 5, 6), (53, '1142', 'O-214', 5, 7);

-- 1151 已選（尚未登分）
INSERT INTO Enrollment (student_id, section_id, status) VALUES
('S004', 34, 'Selected'),
('S005', 34, 'Selected'),
('S014', 34, 'Selected'),
('S016', 34, 'Selected'),
('S013', 35, 'Selected'),
('S017', 35, 'Selected'),
('S022', 35, 'Selected'),
('S014', 36, 'Selected'),
('S016', 36, 'Selected'),
('S011', 37, 'Selected'),
('S013', 37, 'Selected'),
('S015', 37, 'Selected'),
('S022', 37, 'Selected'),
('S009', 38, 'Selected'),
('S018', 38, 'Selected'),
('S018', 39, 'Selected'),
('S019', 39, 'Selected'),
('S006', 40, 'Selected'),
('S007', 40, 'Selected'),
('S012', 40, 'Selected'),
('S007', 41, 'Selected'),
('S020', 41, 'Selected'),
('S021', 41, 'Selected'),
('S006', 42, 'Selected'),
('S020', 42, 'Selected'),
('S003', 43, 'Selected'),
('S012', 43, 'Selected');

-- 歷史學期的修課與成績
INSERT INTO Enrollment (student_id, section_id, status, score, feedback_rank) VALUES
-- 1131 A0011 微積分（岳飛）
('S003', 44, 'Selected', 85, 8),
('S004', 44, 'Selected', 74, 7),
('S009', 44, 'Selected', 58, 5),
('S014', 44, 'Selected', 90, 9),
('S016', 44, 'Selected', 88, 9),
('S017', 44, 'Selected', 72, 6),
('S022', 44, 'Selected', 66, 6),
-- 1131 A0017 英文寫作
('S001', 45, 'Selected', 80, 8),
('S006', 45, 'Selected', 77, 7),
('S012', 45, 'Selected', 92, 10),
('S020', 45, 'Selected', 69, 6),
('S021', 45, 'Selected', 83, 8),
-- 1132 A0012 離散數學
('S011', 46, 'Selected', 65, 6),
('S013', 46, 'Selected', 78, 7),
('S015', 46, 'Selected', 57, 4),
('S016', 46, 'Selected', 94, 10),
('S017', 46, 'Selected', 81, 8),
('S022', 46, 'Selected', 73, 7),
-- 1132 A0019 哲學概論
('S005', 47, 'Selected', 86, 9),
('S006', 47, 'Selected', 71, 7),
('S007', 47, 'Selected', 63, 6),
('S012', 47, 'Selected', 88, 9),
('S020', 47, 'Selected', 79, 8),
-- 1141 A0011 微積分（莊周）
('S005', 48, 'Selected', 77, 7),
('S007', 48, 'Selected', 69, 6),
('S011', 48, 'Selected', 82, 8),
('S013', 48, 'Selected', 61, 5),
('S015', 48, 'Selected', 90, 9),
('S019', 48, 'Selected', 54, 4),
-- 1141 A0013 機率論
('S003', 49, 'Selected', 84, 8),
('S014', 49, 'Selected', 88, 9),
('S016', 49, 'Selected', 97, 10),
('S017', 49, 'Selected', 76, 7),
('S022', 49, 'Selected', 70, 6),
-- 1141 A0015 作業系統
('S009', 50, 'Selected', 79, 8),
('S011', 50, 'Selected', 73, 7),
('S013', 50, 'Selected', 68, 6),
('S015', 50, 'Selected', 85, 8),
('S018', 50, 'Selected', 62, 5),
-- 1142 A0014 機器學習
('S011', 51, 'Selected', 88, 9),
('S013', 51, 'Selected', 74, 7),
('S014', 51, 'Selected', 95, 10),
('S016', 51, 'Selected', 91, 9),
('S017', 51, 'Manual', 67, 6),
('S022', 51, 'Selected', 80, 8),
-- 1142 A0016 計算機網路
('S009', 52, 'Selected', 76, 7),
('S012', 52, 'Selected', 72, 7),
('S015', 52, 'Selected', 81, 8),
('S018', 52, 'Selected', 59, 5),
('S019', 52, 'Selected', 65, 6),
-- 1142 A0018 投資學
('S001', 53, 'Selected', 71, 7),
('S004', 53, 'Selected', 63, 6),
('S007', 53, 'Selected', 78, 8),
('S012', 53, 'Selected', 84, 9),
('S020', 53, 'Selected', 55, 4),
('S021', 53, 'Selected', 69, 6);
