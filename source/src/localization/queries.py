CREATE_TABLE_TICKETS: str = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id VARCHAR(64) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    message_chat_id BIGINT NOT NULL,
    username VARCHAR(255) NOT NULL,
    userfullname VARCHAR(500) NOT NULL,
    issue TEXT NOT NULL,
    status ENUM('open', 'closed', 'in_progress') DEFAULT 'open',
    handler_id BIGINT NULL,
    handler_username VARCHAR(255) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_handler_id (handler_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_TABLE_TICKET_MESSAGES: str = """
CREATE TABLE IF NOT EXISTS ticket_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id VARCHAR(64) NOT NULL,
    user_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    message_chat_id BIGINT NOT NULL,
    username VARCHAR(255) NOT NULL,
    userfullname VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    message_from ENUM('admin', 'user', 'handler') DEFAULT 'user',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    INDEX idx_ticket_id (ticket_id),
    INDEX idx_user_id (user_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_TABLE_USERS_DETAILS: str = """
CREATE TABLE IF NOT EXISTS usersv2 (
    id BIGINT PRIMARY KEY,
    is_bot BOOLEAN,
    first_name VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    last_name VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_TABLE_BANNED_USERS: str = """
CREATE TABLE IF NOT EXISTS banned_users (
    user_id BIGINT PRIMARY KEY,
    reason TEXT,
    banned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NULL,
    banned_by BIGINT NULL,
    INDEX idx_banned_at (banned_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_TABLE_HANDLERS: str = """
CREATE TABLE IF NOT EXISTS handlersv2 (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_username (username),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

GET_ALL_TABLES: str = """
SELECT TABLE_NAME 
FROM information_schema.tables 
WHERE TABLE_SCHEMA = %s;
"""

INSERT_USER_FOR_HANDLER: str = """
INSERT IGNORE INTO handlersv2 (user_id, username) VALUES (%s, %s)
"""

DELETE_USER_FROM_HANDLER: str = """
DELETE FROM handlersv2 WHERE user_id = %s;
"""

GET_ALL_HANDLERS: str = """
SELECT * FROM handlersv2
"""

CHECK_USER_IS_HANDLER: str = """
SELECT COUNT(*) FROM handlersv2 WHERE user_id = %s
"""

CREATE_TICKET: str = """
INSERT INTO tickets (ticket_id, user_id, message_id, message_chat_id, username, userfullname, issue, created_at, status) 
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

ADDED_USER_DETAILS: str = """
INSERT INTO usersv2 (id, is_bot, first_name, username, last_name)
VALUES (%s, %s, %s, %s, %s)
"""

UPDATE_USER_DETAILS: str = """
UPDATE usersv2
SET first_name = %s, username = %s, last_name = %s
WHERE id = %s
"""

ADDED_TICKET_MESSAGE: str = """
INSERT INTO ticket_messages (ticket_id, user_id, message_id, message_chat_id, username, userfullname, message, message_from, timestamp) 
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

GET_TICKET_BY_ID: str = """
SELECT * FROM tickets WHERE ticket_id = %s
"""

GET_USER_DETAILS_BY_ID: str = """
SELECT * FROM usersv2 WHERE id = %s
"""

GET_TICKET_MESSAGES: str = """
SELECT COUNT(*) AS count FROM tickets 
WHERE ticket_id = %s AND user_id = %s
"""

GET_ALL_TICKET_MESSAGES: str = """
SELECT username, userfullname, message, timestamp 
FROM ticket_messages
WHERE ticket_id = %s 
ORDER BY timestamp ASC
"""

CLOSED_TICKET: str = """
UPDATE tickets 
SET status = 'closed', handler_id = %s, handler_username = %s, closed_at = %s 
WHERE ticket_id = %s AND status = 'open'
"""

GET_USER_TICKETS: str = """
SELECT ticket_id, user_id, message_id, message_chat_id, issue, status, created_at, closed_at, handler_username 
FROM tickets 
WHERE user_id = %s AND status = 'open'
ORDER BY created_at DESC
"""

GET_CLOSED_TICKETS_BY_TICKETID: str = """
SELECT ticket_id, handler_username, closed_at 
FROM tickets 
WHERE ticket_id = %s AND status = 'closed'
ORDER BY closed_at DESC
"""

GET_CLOSED_TICKETS: str = """
SELECT ticket_id, issue, created_at, closed_at 
FROM tickets 
WHERE user_id = %s AND status = 'closed'
ORDER BY closed_at DESC
"""

GET_HISTORY_HANDLER_TICKETS: str = """
SELECT ticket_id, issue, status, created_at, closed_at, handler_username 
FROM tickets
WHERE handler_id = %s 
  AND DATE(closed_at) = CURDATE() 
ORDER BY closed_at ASC
"""

GET_HISTORY_USER_TICKETS: str = """
SELECT ticket_id, issue, status, created_at, closed_at, handler_username 
FROM tickets
WHERE user_id = %s 
""" 

GET_OPENED_TICKETS: str = """
SELECT ticket_id, username, message_id, message_chat_id, userfullname, created_at 
FROM tickets 
WHERE status = 'open'
ORDER BY created_at DESC
"""

GET_USER_BY_USERNAME: str = """
SELECT id FROM usersv2 WHERE username = %s
"""