-- CreateTable
CREATE TABLE `UserAccount` (
    `user_id` INTEGER NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(30) NOT NULL,
    `password_hash` VARCHAR(100) NOT NULL,
    `role` ENUM('Admin', 'Teacher', 'Student') NOT NULL,
    `is_active` BOOLEAN NOT NULL DEFAULT true,
    `created_at` DATETIME(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
    `last_login_at` DATETIME(0) NULL,

    UNIQUE INDEX `UserAccount_username_key`(`username`),
    PRIMARY KEY (`user_id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Department` (
    `dept_id` CHAR(4) NOT NULL,
    `dept_name` VARCHAR(50) NOT NULL,

    UNIQUE INDEX `Department_dept_name_key`(`dept_name`),
    PRIMARY KEY (`dept_id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Teacher` (
    `teacher_id` CHAR(6) NOT NULL,
    `teacher_name` VARCHAR(50) NOT NULL,
    `dept_id` CHAR(4) NULL,
    `can_open_section` BOOLEAN NOT NULL DEFAULT false,
    `user_id` INTEGER NULL,

    UNIQUE INDEX `Teacher_user_id_key`(`user_id`),
    PRIMARY KEY (`teacher_id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `TeacherPermissionLog` (
    `log_id` INTEGER NOT NULL AUTO_INCREMENT,
    `teacher_id` CHAR(6) NOT NULL,
    `granted` BOOLEAN NOT NULL,
    `changed_by` INTEGER NOT NULL,
    `changed_at` DATETIME(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),

    INDEX `TeacherPermissionLog_teacher_id_changed_at_idx`(`teacher_id`, `changed_at`),
    PRIMARY KEY (`log_id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Student` (
    `student_id` CHAR(10) NOT NULL,
    `student_name` VARCHAR(30) NOT NULL,
    `dept_id` CHAR(4) NOT NULL,
    `grade` TINYINT NOT NULL,
    `status` ENUM('Enrolled', 'Suspended', 'Dropped') NOT NULL,
    `class_code` CHAR(2) NOT NULL,
    `degree` TINYINT NOT NULL DEFAULT 0,
    `user_id` INTEGER NULL,

    UNIQUE INDEX `Student_user_id_key`(`user_id`),
    PRIMARY KEY (`student_id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Building` (
    `building_id` CHAR(4) NOT NULL,
    `building_name` VARCHAR(50) NOT NULL,

    UNIQUE INDEX `Building_building_name_key`(`building_name`),
    PRIMARY KEY (`building_id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Room` (
    `room_code` VARCHAR(10) NOT NULL,
    `building_id` CHAR(4) NOT NULL,
    `seat_capacity` SMALLINT NULL,

    PRIMARY KEY (`room_code`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Course` (
    `course_no` CHAR(5) NOT NULL,
    `course_name` VARCHAR(50) NOT NULL,
    `course_type` ENUM('Required', 'Elective') NOT NULL,
    `credit` TINYINT NOT NULL,
    `dept_id` CHAR(4) NULL,
    `is_active` BOOLEAN NOT NULL DEFAULT true,

    PRIMARY KEY (`course_no`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `CurriculumField` (
    `course_no` CHAR(5) NOT NULL,
    `field_name` VARCHAR(50) NOT NULL,

    PRIMARY KEY (`course_no`, `field_name`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Semester` (
    `semester_id` CHAR(4) NOT NULL,
    `acad_year` SMALLINT NOT NULL,
    `term` TINYINT NOT NULL,
    `status` ENUM('Planning', 'Enrolling', 'InProgress', 'Finished') NOT NULL DEFAULT 'Planning',
    `is_current` BOOLEAN NOT NULL DEFAULT false,

    UNIQUE INDEX `Semester_acad_year_term_key`(`acad_year`, `term`),
    PRIMARY KEY (`semester_id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Section` (
    `section_id` INTEGER NOT NULL AUTO_INCREMENT,
    `course_no` CHAR(5) NOT NULL,
    `semester_id` CHAR(4) NOT NULL,
    `section_code` CHAR(2) NOT NULL DEFAULT '01',
    `capacity` SMALLINT NOT NULL,
    `status` ENUM('Open', 'Cancelled') NOT NULL DEFAULT 'Open',
    `created_by` CHAR(6) NULL,
    `created_at` DATETIME(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),

    INDEX `Section_semester_id_status_idx`(`semester_id`, `status`),
    UNIQUE INDEX `Section_course_no_semester_id_section_code_key`(`course_no`, `semester_id`, `section_code`),
    UNIQUE INDEX `Section_section_id_semester_id_key`(`section_id`, `semester_id`),
    PRIMARY KEY (`section_id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `SectionTeacher` (
    `section_id` INTEGER NOT NULL,
    `teacher_id` CHAR(6) NOT NULL,
    `is_primary` BOOLEAN NOT NULL DEFAULT true,

    INDEX `SectionTeacher_teacher_id_idx`(`teacher_id`),
    PRIMARY KEY (`section_id`, `teacher_id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `SectionSchedule` (
    `schedule_id` INTEGER NOT NULL AUTO_INCREMENT,
    `section_id` INTEGER NOT NULL,
    `semester_id` CHAR(4) NOT NULL,
    `room_code` VARCHAR(10) NOT NULL,
    `weekday` TINYINT NOT NULL,
    `period` TINYINT NOT NULL,

    INDEX `SectionSchedule_room_code_idx`(`room_code`),
    UNIQUE INDEX `SectionSchedule_section_id_weekday_period_key`(`section_id`, `weekday`, `period`),
    UNIQUE INDEX `uq_room_timeslot`(`semester_id`, `room_code`, `weekday`, `period`),
    PRIMARY KEY (`schedule_id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Enrollment` (
    `student_id` CHAR(10) NOT NULL,
    `section_id` INTEGER NOT NULL,
    `status` ENUM('Registered', 'Selected', 'Manual', 'NotSelected', 'Withdrawn') NOT NULL,
    `score` DECIMAL(4, 1) NULL,
    `feedback_rank` TINYINT NULL,
    `enrolled_at` DATETIME(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
    `updated_at` DATETIME(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),

    INDEX `Enrollment_section_id_status_idx`(`section_id`, `status`),
    PRIMARY KEY (`student_id`, `section_id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `ScoreChangeLog` (
    `log_id` INTEGER NOT NULL AUTO_INCREMENT,
    `student_id` CHAR(10) NOT NULL,
    `section_id` INTEGER NOT NULL,
    `old_score` DECIMAL(4, 1) NULL,
    `new_score` DECIMAL(4, 1) NULL,
    `changed_by` INTEGER NOT NULL,
    `changed_at` DATETIME(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),

    INDEX `ScoreChangeLog_student_id_section_id_idx`(`student_id`, `section_id`),
    PRIMARY KEY (`log_id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- AddForeignKey
ALTER TABLE `Teacher` ADD CONSTRAINT `Teacher_dept_id_fkey` FOREIGN KEY (`dept_id`) REFERENCES `Department`(`dept_id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Teacher` ADD CONSTRAINT `Teacher_user_id_fkey` FOREIGN KEY (`user_id`) REFERENCES `UserAccount`(`user_id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `TeacherPermissionLog` ADD CONSTRAINT `TeacherPermissionLog_teacher_id_fkey` FOREIGN KEY (`teacher_id`) REFERENCES `Teacher`(`teacher_id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `TeacherPermissionLog` ADD CONSTRAINT `TeacherPermissionLog_changed_by_fkey` FOREIGN KEY (`changed_by`) REFERENCES `UserAccount`(`user_id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Student` ADD CONSTRAINT `Student_dept_id_fkey` FOREIGN KEY (`dept_id`) REFERENCES `Department`(`dept_id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Student` ADD CONSTRAINT `Student_user_id_fkey` FOREIGN KEY (`user_id`) REFERENCES `UserAccount`(`user_id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Room` ADD CONSTRAINT `Room_building_id_fkey` FOREIGN KEY (`building_id`) REFERENCES `Building`(`building_id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Course` ADD CONSTRAINT `Course_dept_id_fkey` FOREIGN KEY (`dept_id`) REFERENCES `Department`(`dept_id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `CurriculumField` ADD CONSTRAINT `CurriculumField_course_no_fkey` FOREIGN KEY (`course_no`) REFERENCES `Course`(`course_no`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Section` ADD CONSTRAINT `Section_course_no_fkey` FOREIGN KEY (`course_no`) REFERENCES `Course`(`course_no`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Section` ADD CONSTRAINT `Section_semester_id_fkey` FOREIGN KEY (`semester_id`) REFERENCES `Semester`(`semester_id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Section` ADD CONSTRAINT `Section_created_by_fkey` FOREIGN KEY (`created_by`) REFERENCES `Teacher`(`teacher_id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `SectionTeacher` ADD CONSTRAINT `SectionTeacher_section_id_fkey` FOREIGN KEY (`section_id`) REFERENCES `Section`(`section_id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `SectionTeacher` ADD CONSTRAINT `SectionTeacher_teacher_id_fkey` FOREIGN KEY (`teacher_id`) REFERENCES `Teacher`(`teacher_id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `SectionSchedule` ADD CONSTRAINT `SectionSchedule_section_id_semester_id_fkey` FOREIGN KEY (`section_id`, `semester_id`) REFERENCES `Section`(`section_id`, `semester_id`) ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `SectionSchedule` ADD CONSTRAINT `SectionSchedule_room_code_fkey` FOREIGN KEY (`room_code`) REFERENCES `Room`(`room_code`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Enrollment` ADD CONSTRAINT `Enrollment_student_id_fkey` FOREIGN KEY (`student_id`) REFERENCES `Student`(`student_id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Enrollment` ADD CONSTRAINT `Enrollment_section_id_fkey` FOREIGN KEY (`section_id`) REFERENCES `Section`(`section_id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `ScoreChangeLog` ADD CONSTRAINT `ScoreChangeLog_student_id_section_id_fkey` FOREIGN KEY (`student_id`, `section_id`) REFERENCES `Enrollment`(`student_id`, `section_id`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `ScoreChangeLog` ADD CONSTRAINT `ScoreChangeLog_changed_by_fkey` FOREIGN KEY (`changed_by`) REFERENCES `UserAccount`(`user_id`) ON DELETE RESTRICT ON UPDATE CASCADE;
