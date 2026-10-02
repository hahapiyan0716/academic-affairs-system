-- Department 表：儲存系所資訊
CREATE TABLE IF NOT EXISTS Department(
	dept_id CHAR(4) PRIMARY KEY, -- 系所代碼，主鍵
    dept_name VARCHAR(50) UNIQUE NOT NULL -- 系所名稱
);

-- Teacher 表：儲存教師資訊
CREATE TABLE IF NOT EXISTS Teacher (
    teacher_id CHAR(6) PRIMARY KEY, -- 教師代碼，主鍵
    teacher_name VARCHAR(50) UNIQUE NOT NULL -- 教師姓名
);

-- Building 表：儲存大樓資訊
CREATE TABLE IF NOT EXISTS Building (
    building_id CHAR(4) PRIMARY KEY, -- 大樓代碼，主鍵
    building_name VARCHAR(50) UNIQUE NOT NULL -- 大樓名稱
);

-- Room 表：儲存教室資訊
CREATE TABLE IF NOT EXISTS Room (
    room_code VARCHAR(10) PRIMARY KEY, -- 教室編碼，主鍵
    building_id CHAR(4) NOT NULL, -- 所屬大樓代碼，外鍵
    FOREIGN KEY (building_id) REFERENCES Building(building_id) -- 外鍵，參考 Building 表
);

-- Student 表：儲存學生基本資料，與 Department 表關聯
CREATE TABLE IF NOT EXISTS Student (
    student_id CHAR(10) PRIMARY KEY, -- 學號，主鍵
    student_name VARCHAR(30) NOT NULL, -- 學生姓名
    dept_id CHAR(4) NOT NULL, -- 系所代碼，外鍵
    grade TINYINT NOT NULL, -- 年級
							-- TINYINT 只能儲存整數，而且是非常小的整數，儲存空間：只佔用 1 Byte (8 bits)。
	status ENUM('Enrolled', 'Suspended', 'Dropped') NOT NULL, -- 在學狀態：已註冊、休學、退學
    class_code CHAR(2) NOT NULL, -- 班別
    degree INT NOT NULL DEFAULT 0, -- 學位：0 為大學部學生，1 為碩博學生 
    FOREIGN KEY (dept_id) REFERENCES Department(dept_id) -- 外鍵，參考 Department 表
);

-- Course 表：儲存課程基本資訊
CREATE TABLE IF NOT EXISTS Course (
    course_no CHAR(5) PRIMARY KEY, -- 課程編號，主鍵
    course_name VARCHAR(50) NOT NULL, -- 課程名稱
    course_type ENUM('Required', 'Elective') NOT NULL, -- 課程類型：必修或選修
    credit TINYINT NOT NULL, -- 學分數
    capacity SMALLINT NOT NULL, 	-- 人數上限
								-- SMALLINT 儲存空間：佔用 2 Bytes (16 bits)。
	status ENUM('Open', 'Cancelled') NOT NULL -- 開課狀態：開課或取消
);

-- CourseSchedule 表：儲存課程的單一上課時段和教室資訊
CREATE TABLE IF NOT EXISTS CourseSchedule (
    schedule_id BIGINT AUTO_INCREMENT PRIMARY KEY, -- 時段流水號，主鍵，自增
												   -- BIGINT 佔用 8 Bytes，為了防止 ID 用完
                                                   -- AUTO_INCREMENT 自動遞增，當你新增第一筆資料，系統自動填入 1，第二筆資料，系統自動填入 2，依此類推。
    course_no CHAR(5) NOT NULL, -- 課程編號，外鍵
    room_code VARCHAR(10) NOT NULL, -- 教室編碼，外鍵
    time_slot VARCHAR(10) NOT NULL, -- 上課時段
    FOREIGN KEY (course_no) REFERENCES Course(course_no), -- 外鍵，參考 Course 表
    FOREIGN KEY (room_code) REFERENCES Room(room_code) -- 外鍵，參考 Room 表
);

-- CourseTeacher 表：處理課程與教師的多對多關係
CREATE TABLE IF NOT EXISTS CourseTeacher (
    course_no CHAR(5), -- 課程編號，主鍵+外鍵
    teacher_id CHAR(6), -- 教師代碼，主鍵+外鍵
    PRIMARY KEY (course_no, teacher_id), -- 複合主鍵
    FOREIGN KEY (course_no) REFERENCES Course(course_no), -- 外鍵，參考 Course 表
    FOREIGN KEY (teacher_id) REFERENCES Teacher(teacher_id) -- 外鍵，參考 Teacher 表
);

-- CourseSelection 表：儲存學生選課結果、成績和教學評量
CREATE TABLE IF NOT EXISTS CourseSelection (
    student_id CHAR(8), -- 學號，主鍵+外鍵
    course_no CHAR(5), -- 課程編號，主鍵+外鍵
    semester CHAR(4), -- 學期，主鍵
    select_result ENUM('Selected', 'Manual', 'Dropped') NOT NULL, -- 選課結果：中選、人工加選、落選
																  -- ENUM 列舉 (Enumeration)，只能存入 'Selected'、'Manual' 或 'Dropped' 這三個值的其中之一。
                                                                  -- 如果試圖存入 'Pending' 或 'Failed'（不在名單內的值），資料庫會報錯拒絕存入。
    score DECIMAL(4,1), -- 成績
						-- DECIMAL 定點數 (Fixed-Point Number)，4 (Precision，精確度)： 代表這個數字總共最多可以有 4 個位數（包含整數部分和小數部分，但不包含小數點本身）。
						-- 									    1 (Scale，標度)： 代表小數點後面固定有 1 個位數。
                        -- 										例如：80.9
	feedback_rank TINYINT, -- 教學評量
    PRIMARY KEY (student_id, course_no, semester), -- 複合主鍵
    FOREIGN KEY (student_id) REFERENCES Student(student_id), -- 外鍵，參考 Student 表
    FOREIGN KEY (course_no) REFERENCES Course(course_no) -- 外鍵，參考 Course 表
);

-- CurriculumField 表：處理課程與領域的多對多關係
CREATE TABLE IF NOT EXISTS CurriculumField (
    course_no CHAR(5), -- 課程編號，主鍵+外鍵
    field_name VARCHAR(50), -- 課程領域，主鍵
    PRIMARY KEY (course_no, field_name), -- 複合主鍵
    FOREIGN KEY (course_no) REFERENCES Course(course_no) -- 外鍵，參考 Course 表
);