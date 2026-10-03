-- 由 Alembic 離線模式產生的完整建表 SQL（閱讀與對照用，不需手動執行）
-- 產生方式：在 services/api 下執行 alembic upgrade head --sql
-- 資料庫結構的唯一來源是 services/api/app/models.py

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE `Building` (
    building_id CHAR(4) NOT NULL, 
    building_name VARCHAR(50) NOT NULL, 
    PRIMARY KEY (building_id), 
    CONSTRAINT `Building_building_name_key` UNIQUE (building_name)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `Department` (
    dept_id CHAR(4) NOT NULL, 
    dept_name VARCHAR(50) NOT NULL, 
    PRIMARY KEY (dept_id), 
    CONSTRAINT `Department_dept_name_key` UNIQUE (dept_name)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `Semester` (
    semester_id CHAR(4) NOT NULL, 
    acad_year SMALLINT NOT NULL, 
    term TINYINT NOT NULL, 
    status ENUM('Planning','Enrolling','InProgress','Finished') NOT NULL DEFAULT 'Planning', 
    is_current BOOL NOT NULL DEFAULT 0, 
    PRIMARY KEY (semester_id), 
    CONSTRAINT chk_semester_term CHECK (term IN (1, 2, 3)), 
    CONSTRAINT `Semester_acad_year_term_key` UNIQUE (acad_year, term)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `UserAccount` (
    user_id INTEGER NOT NULL AUTO_INCREMENT, 
    username VARCHAR(30) NOT NULL, 
    password_hash VARCHAR(100) NOT NULL, 
    `role` ENUM('Admin','Teacher','Student') NOT NULL, 
    is_active BOOL NOT NULL DEFAULT 1, 
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
    last_login_at DATETIME, 
    PRIMARY KEY (user_id), 
    CONSTRAINT `UserAccount_username_key` UNIQUE (username)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `Course` (
    course_no CHAR(5) NOT NULL, 
    course_name VARCHAR(50) NOT NULL, 
    course_type ENUM('Required','Elective') NOT NULL, 
    credit TINYINT NOT NULL, 
    dept_id CHAR(4), 
    is_active BOOL NOT NULL DEFAULT 1, 
    PRIMARY KEY (course_no), 
    CONSTRAINT chk_course_credit CHECK (credit BETWEEN 0 AND 10), 
    CONSTRAINT `Course_dept_id_fkey` FOREIGN KEY(dept_id) REFERENCES `Department` (dept_id) ON DELETE SET NULL ON UPDATE CASCADE
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `Room` (
    room_code VARCHAR(10) NOT NULL, 
    building_id CHAR(4) NOT NULL, 
    seat_capacity SMALLINT, 
    PRIMARY KEY (room_code), 
    CONSTRAINT `Room_building_id_fkey` FOREIGN KEY(building_id) REFERENCES `Building` (building_id) ON DELETE RESTRICT ON UPDATE CASCADE
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `Student` (
    student_id CHAR(10) NOT NULL, 
    student_name VARCHAR(30) NOT NULL, 
    dept_id CHAR(4) NOT NULL, 
    grade TINYINT NOT NULL, 
    status ENUM('Enrolled','Suspended','Dropped') NOT NULL, 
    class_code CHAR(2) NOT NULL, 
    degree TINYINT NOT NULL DEFAULT 0, 
    user_id INTEGER, 
    PRIMARY KEY (student_id), 
    CONSTRAINT `Student_dept_id_fkey` FOREIGN KEY(dept_id) REFERENCES `Department` (dept_id) ON DELETE RESTRICT ON UPDATE CASCADE, 
    CONSTRAINT `Student_user_id_fkey` FOREIGN KEY(user_id) REFERENCES `UserAccount` (user_id) ON DELETE SET NULL ON UPDATE CASCADE, 
    CONSTRAINT `Student_user_id_key` UNIQUE (user_id)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `Teacher` (
    teacher_id CHAR(6) NOT NULL, 
    teacher_name VARCHAR(50) NOT NULL, 
    dept_id CHAR(4), 
    can_open_section BOOL NOT NULL DEFAULT 0, 
    user_id INTEGER, 
    PRIMARY KEY (teacher_id), 
    CONSTRAINT `Teacher_dept_id_fkey` FOREIGN KEY(dept_id) REFERENCES `Department` (dept_id) ON DELETE SET NULL ON UPDATE CASCADE, 
    CONSTRAINT `Teacher_user_id_fkey` FOREIGN KEY(user_id) REFERENCES `UserAccount` (user_id) ON DELETE SET NULL ON UPDATE CASCADE, 
    CONSTRAINT `Teacher_user_id_key` UNIQUE (user_id)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `CurriculumField` (
    course_no CHAR(5) NOT NULL, 
    field_name VARCHAR(50) NOT NULL, 
    PRIMARY KEY (course_no, field_name), 
    CONSTRAINT `CurriculumField_course_no_fkey` FOREIGN KEY(course_no) REFERENCES `Course` (course_no) ON DELETE CASCADE ON UPDATE CASCADE
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE `Section` (
    section_id INTEGER NOT NULL AUTO_INCREMENT, 
    course_no CHAR(5) NOT NULL, 
    semester_id CHAR(4) NOT NULL, 
    section_code CHAR(2) NOT NULL DEFAULT '01', 
    capacity SMALLINT NOT NULL, 
    status ENUM('Open','Cancelled') NOT NULL DEFAULT 'Open', 
    created_by CHAR(6), 
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
    PRIMARY KEY (section_id), 
    CONSTRAINT chk_section_capacity CHECK (capacity BETWEEN 1 AND 500), 
    CONSTRAINT `Section_course_no_fkey` FOREIGN KEY(course_no) REFERENCES `Course` (course_no) ON DELETE RESTRICT ON UPDATE CASCADE, 
    CONSTRAINT `Section_created_by_fkey` FOREIGN KEY(created_by) REFERENCES `Teacher` (teacher_id) ON DELETE SET NULL ON UPDATE CASCADE, 
    CONSTRAINT `Section_semester_id_fkey` FOREIGN KEY(semester_id) REFERENCES `Semester` (semester_id) ON DELETE RESTRICT ON UPDATE CASCADE, 
    CONSTRAINT `Section_course_no_semester_id_section_code_key` UNIQUE (course_no, semester_id, section_code), 
    CONSTRAINT `Section_section_id_semester_id_key` UNIQUE (section_id, semester_id)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE INDEX `Section_semester_id_status_idx` ON `Section` (semester_id, status);

CREATE TABLE `TeacherPermissionLog` (
    log_id INTEGER NOT NULL AUTO_INCREMENT, 
    teacher_id CHAR(6) NOT NULL, 
    granted BOOL NOT NULL, 
    changed_by INTEGER NOT NULL, 
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
    PRIMARY KEY (log_id), 
    CONSTRAINT `TeacherPermissionLog_changed_by_fkey` FOREIGN KEY(changed_by) REFERENCES `UserAccount` (user_id) ON DELETE RESTRICT ON UPDATE CASCADE, 
    CONSTRAINT `TeacherPermissionLog_teacher_id_fkey` FOREIGN KEY(teacher_id) REFERENCES `Teacher` (teacher_id) ON DELETE RESTRICT ON UPDATE CASCADE
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE INDEX `TeacherPermissionLog_teacher_id_changed_at_idx` ON `TeacherPermissionLog` (teacher_id, changed_at);

CREATE TABLE `Enrollment` (
    student_id CHAR(10) NOT NULL, 
    section_id INTEGER NOT NULL, 
    status ENUM('Registered','Selected','Manual','NotSelected','Withdrawn') NOT NULL, 
    score DECIMAL(4, 1), 
    feedback_rank TINYINT, 
    enrolled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
    PRIMARY KEY (student_id, section_id), 
    CONSTRAINT chk_enrollment_feedback CHECK (feedback_rank IS NULL OR feedback_rank BETWEEN 1 AND 10), 
    CONSTRAINT chk_enrollment_score CHECK (score IS NULL OR score BETWEEN 0 AND 100), 
    CONSTRAINT `Enrollment_section_id_fkey` FOREIGN KEY(section_id) REFERENCES `Section` (section_id) ON DELETE RESTRICT ON UPDATE CASCADE, 
    CONSTRAINT `Enrollment_student_id_fkey` FOREIGN KEY(student_id) REFERENCES `Student` (student_id) ON DELETE RESTRICT ON UPDATE CASCADE
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE INDEX `Enrollment_section_id_status_idx` ON `Enrollment` (section_id, status);

CREATE TABLE `SectionSchedule` (
    schedule_id INTEGER NOT NULL AUTO_INCREMENT, 
    section_id INTEGER NOT NULL, 
    semester_id CHAR(4) NOT NULL, 
    room_code VARCHAR(10) NOT NULL, 
    weekday TINYINT NOT NULL, 
    period TINYINT NOT NULL, 
    PRIMARY KEY (schedule_id), 
    CONSTRAINT chk_schedule_period CHECK (period BETWEEN 1 AND 14), 
    CONSTRAINT chk_schedule_weekday CHECK (weekday BETWEEN 1 AND 7), 
    CONSTRAINT `SectionSchedule_room_code_fkey` FOREIGN KEY(room_code) REFERENCES `Room` (room_code) ON DELETE RESTRICT ON UPDATE CASCADE, 
    CONSTRAINT `SectionSchedule_section_id_semester_id_fkey` FOREIGN KEY(section_id, semester_id) REFERENCES `Section` (section_id, semester_id) ON DELETE CASCADE ON UPDATE CASCADE, 
    CONSTRAINT `SectionSchedule_section_id_weekday_period_key` UNIQUE (section_id, weekday, period), 
    CONSTRAINT uq_room_timeslot UNIQUE (semester_id, room_code, weekday, period)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE INDEX `SectionSchedule_room_code_idx` ON `SectionSchedule` (room_code);

CREATE TABLE `SectionTeacher` (
    section_id INTEGER NOT NULL, 
    teacher_id CHAR(6) NOT NULL, 
    is_primary BOOL NOT NULL DEFAULT 1, 
    PRIMARY KEY (section_id, teacher_id), 
    CONSTRAINT `SectionTeacher_section_id_fkey` FOREIGN KEY(section_id) REFERENCES `Section` (section_id) ON DELETE CASCADE ON UPDATE CASCADE, 
    CONSTRAINT `SectionTeacher_teacher_id_fkey` FOREIGN KEY(teacher_id) REFERENCES `Teacher` (teacher_id) ON DELETE RESTRICT ON UPDATE CASCADE
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE INDEX `SectionTeacher_teacher_id_idx` ON `SectionTeacher` (teacher_id);

CREATE TABLE `ScoreChangeLog` (
    log_id INTEGER NOT NULL AUTO_INCREMENT, 
    student_id CHAR(10) NOT NULL, 
    section_id INTEGER NOT NULL, 
    old_score DECIMAL(4, 1), 
    new_score DECIMAL(4, 1), 
    changed_by INTEGER NOT NULL, 
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
    PRIMARY KEY (log_id), 
    CONSTRAINT `ScoreChangeLog_changed_by_fkey` FOREIGN KEY(changed_by) REFERENCES `UserAccount` (user_id) ON DELETE RESTRICT ON UPDATE CASCADE, 
    CONSTRAINT `ScoreChangeLog_student_id_section_id_fkey` FOREIGN KEY(student_id, section_id) REFERENCES `Enrollment` (student_id, section_id) ON DELETE RESTRICT ON UPDATE CASCADE
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE INDEX `ScoreChangeLog_student_id_section_id_idx` ON `ScoreChangeLog` (student_id, section_id);

CREATE VIEW `v_section_detail` AS
SELECT
    s.section_id,
    s.semester_id,
    s.course_no,
    c.course_name,
    c.course_type,
    c.credit,
    s.section_code,
    s.capacity,
    s.status,
    s.created_by,
    (SELECT GROUP_CONCAT(t.teacher_name ORDER BY st.is_primary DESC, t.teacher_id SEPARATOR '、')
       FROM `SectionTeacher` st
       JOIN `Teacher` t ON t.teacher_id = st.teacher_id
      WHERE st.section_id = s.section_id) AS teacher_names,
    (SELECT GROUP_CONCAT(
                CONCAT(ELT(ss.weekday, '一', '二', '三', '四', '五', '六', '日'), ss.period, '@', ss.room_code)
                ORDER BY ss.weekday, ss.period SEPARATOR ',')
       FROM `SectionSchedule` ss
      WHERE ss.section_id = s.section_id) AS schedule_text,
    (SELECT COUNT(*)
       FROM `Enrollment` e
      WHERE e.section_id = s.section_id
        AND e.status IN ('Selected', 'Manual')) AS enrolled_count
FROM `Section` s
JOIN `Course` c ON c.course_no = s.course_no;

CREATE VIEW `v_student_transcript` AS
SELECT
    e.student_id,
    s.semester_id,
    s.section_id,
    c.course_no,
    c.course_name,
    c.course_type,
    c.credit,
    e.status,
    e.score,
    CASE
        WHEN e.score IS NULL THEN NULL
        WHEN e.score >= IF(st.degree = 1, 70, 60) THEN 1
        ELSE 0
    END AS passed
FROM `Enrollment` e
JOIN `Section` s  ON s.section_id = e.section_id
JOIN `Course` c   ON c.course_no = s.course_no
JOIN `Student` st ON st.student_id = e.student_id
WHERE e.status IN ('Selected', 'Manual');

INSERT INTO alembic_version (version_num) VALUES ('0001');

