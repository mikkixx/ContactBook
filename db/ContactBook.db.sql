BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "departments" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL UNIQUE,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "employees" (
	"id"	INTEGER,
	"last_name"	TEXT NOT NULL,
	"first_name"	TEXT NOT NULL,
	"middle_name"	TEXT,
	"department_id"	INTEGER NOT NULL,
	"subdivision_id"	INTEGER,
	"phone"	TEXT UNIQUE,
	"floor"	INTEGER,
	"cabinet"	TEXT,
	"is_active"	BOOLEAN DEFAULT 1,
	"created_at"	DATETIME DEFAULT CURRENT_TIMESTAMP,
	"updated_at"	DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("department_id") REFERENCES "departments"("id"),
	FOREIGN KEY("subdivision_id") REFERENCES "subdivisions"("id")
);
CREATE TABLE IF NOT EXISTS "favorites" (
	"id"	INTEGER,
	"user_id"	INTEGER NOT NULL,
	"employee_id"	INTEGER NOT NULL,
	"created_at"	DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY("id" AUTOINCREMENT),
	UNIQUE("user_id","employee_id"),
	FOREIGN KEY("employee_id") REFERENCES "employees"("id") ON DELETE CASCADE,
	FOREIGN KEY("user_id") REFERENCES "users"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "subdivisions" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL,
	"department_id"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	UNIQUE("name","department_id"),
	FOREIGN KEY("department_id") REFERENCES "departments"("id") ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS "users" (
	"id"	INTEGER,
	"email"	TEXT NOT NULL UNIQUE,
	"password_hash"	TEXT NOT NULL,
	"role"	TEXT NOT NULL DEFAULT 'user' CHECK("role" IN ('user', 'admin')),
	"employee_id"	INTEGER NOT NULL UNIQUE,
	"is_active"	BOOLEAN DEFAULT 1,
	"created_at"	DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("employee_id") REFERENCES "employees"("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_employees_dept" ON "employees" (
	"department_id"
);
CREATE INDEX IF NOT EXISTS "idx_employees_search" ON "employees" (
	"last_name",
	"first_name",
	"phone"
);
CREATE INDEX IF NOT EXISTS "idx_employees_sub" ON "employees" (
	"subdivision_id"
);
CREATE INDEX IF NOT EXISTS "idx_favorites_employee" ON "favorites" (
	"employee_id"
);
CREATE INDEX IF NOT EXISTS "idx_favorites_user" ON "favorites" (
	"user_id"
);
CREATE INDEX IF NOT EXISTS "idx_subdivisions_dept" ON "subdivisions" (
	"department_id"
);
COMMIT;
