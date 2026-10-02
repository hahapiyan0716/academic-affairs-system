-- =====================================================================
-- 種子資料（由 prisma/seed.ts 逐句執行；帳號與密碼雜湊由 seed.ts 產生）
--
-- 1132 學期：完整轉換自原 insert_data.sql
--   * Course 的 capacity / status 移到 Section
--   * CourseSchedule.time_slot '一5' 拆為 weekday = 1、period = 5
--   * CourseTeacher 改為 SectionTeacher
--   * CourseSelection 改為 Enrollment，'Dropped'（落選）改為 'NotSelected'
-- 1141 學期：新增的歷史學期，用來展示「同一門課、不同學期、不同教師」
-- 1151 學期：目前學期（選課中），供加退選與開課展示
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

-- 課程庫：capacity、status 已移至 Section
INSERT INTO Course (course_no, course_name, course_type, credit) VALUES
('A0001', '日文', 'Elective', 2),
('A0002', '計算機概論', 'Required', 3),
('A0003', '統計學習', 'Elective', 3),
('A0004', '經濟學', 'Required', 3),
('A0005', '統計學', 'Elective', 3),
('A0006', '音樂欣賞', 'Elective', 2),
('A0007', '演算法', 'Elective', 3);

-- 註：A0001（日文）歸在「理論數學」領域沿用自原始資料，疑似原始資料錯誤，保留待確認
INSERT INTO CurriculumField (course_no, field_name) VALUES
('A0001', '理論數學'),
('A0002', '基礎知識'),
('A0002', '人工智慧'),
('A0003', '財務工程'),
('A0003', '統計推論'),
('A0004', '基礎知識'),
('A0005', '基礎知識'),
('A0006', '人文思想'),
('A0007', '人工智慧'),
('A0007', '資料科學');

-- ---------------------------------------------------------------------
-- 學期
-- ---------------------------------------------------------------------
INSERT INTO Semester (semester_id, acad_year, term, status, is_current) VALUES
('1132', 113, 2, 'Finished', FALSE),
('1141', 114, 1, 'Finished', FALSE),
('1151', 115, 1, 'Enrolling', TRUE);

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
(2, '1132', 'L102', 2, 3), (2, '1132', 'L102', 2, 4), (2, '1132', 'L102', 5, 4),
(3, '1132', 'M-605', 4, 5), (3, '1132', 'M-605', 4, 6), (3, '1132', 'M-605', 4, 7),
(4, '1132', 'I1-018', 4, 5), (4, '1132', 'I1-018', 4, 6), (4, '1132', 'I1-018', 4, 7),
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
(8, '1141', 'L102', 2, 3), (8, '1141', 'L102', 2, 4), (8, '1141', 'L102', 5, 4),
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
