--CREATE DATABASE db_name;
--CREATE USER db_username@'localhost' IDENTIFIED BY db_user_password;
--GRANT SELECT, INSERT, UPDATE, DELETE ON db_name.* TO db_username@'localhost';
--FLUSH PRIVILEGES;
--USE db_name;

create table if not exists sd (
	request_id varchar(255) not null,
	request_object text not null,
	created_at timestamp not null default (UTC_TIMESTAMP()),
	primary key (request_id),
	INDEX idx_created_at (created_at)
) ENGINE=InnoDB default CHARSET=utf8mb4;

create table if not exists sdo (
	id int not null AUTO_INCREMENT,
	request_id varchar(255) not null,
	signed_data_object mediumtext,
	error varchar(255),
	created_at timestamp not null default (UTC_TIMESTAMP()),
	primary key (id),
	INDEX idx_request_id (request_id)
) ENGINE=InnoDB default CHARSET=utf8mb4;